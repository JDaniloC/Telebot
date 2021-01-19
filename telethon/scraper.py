from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty, InputPeerUser
from telethon.sync import TelegramClient
import json, traceback, asyncio
from telethon import functions
from datetime import datetime
from telethon.errors import *

def get_userprofile(user):
    if user.username:
        username = "@" + user.username
    else:
        username = ""

    if user.first_name:
        first_name = user.first_name
    else:
        first_name = ""
    if user.last_name:
        last_name = user.last_name
    else:
        last_name = ""
    name = username + " - " + (first_name + ' ' + last_name).strip()
    return {
        "id": user.id, 
        "hash": user.access_hash, 
        "name": name
    }

def guarda_usuario(info):
    with open("config/usuarios.json", "r+", encoding = "utf-8") as file:
        lista = json.load(file)
    lista.append(info)
    with open("config/usuarios.json", "w", encoding = "utf-8") as file:
        json.dump(lista, file, indent = 2)

class Telegram:
    def __init__(self):
        self.pausar, self.limitar = 30, 45
        self.offset, self.filtro = 0, 7
        self.usuarios = []
        self.mensagem = {
            "msg": "", "video": False,
            "path": "", "audio": False}
        self.clients = []
        self.output = None
        self.prompt = None
        self.list_groups = None
        self.lista_clients = {}
        self.total_capturado = 0
        self.escolhendo_destino = False

    def adicionar_funcoes(self, output, prompt, list_groups):
        self.output = output
        self.prompt = prompt
        self.list_groups = list_groups

    async def conectar(self):
        '''
        Percorre os contatos se conectando em cada um deles.
        Poderá pedir uma senha do telegram.
        '''
        for user in self.usuarios:
            api_id = user['id']
            api_hash = user['hash']
            numero_celular = user['number']

            client = TelegramClient(
                numero_celular, api_id, api_hash)
            await client.connect()
            if not await client.is_user_authorized():
                self.output(f"Enviando um código para: {numero_celular}.")
                await client.send_code_request(numero_celular)
                try:
                    await client.sign_in(numero_celular, 
                        self.prompt(f"Coloque o código que chegar no número {numero_celular}")())
                    self.clients.append(client)
                    self.output(f"{numero_celular} conectado com sucesso.")
                except PhoneCodeExpiredError:
                    self.output("Você demorou de mais pra colocar o código")
                except PhoneCodeInvalidError:
                    self.output("Código errado!")
            else:
                self.output(f"{numero_celular} conectado com sucesso.")
                self.clients.append(client)
        if len(self.clients) > 0:
            for client in self.clients:
                self.lista_clients[client] = {
                    "alvo": None, "destino": None}
            self.salvar()
            return True
        return False
    
    async def listar_grupos(self, client = None, escolhido = None):
        '''
        Captura um grupo da lista de conversas do client
        '''
        if client is None:
            client = list(self.lista_clients.keys())[0]
        conversas = []
        self.grupos = []

        response = await client(GetDialogsRequest(
                    offset_date = None, hash = 0,
                    offset_id = 0, limit = 100,
                    offset_peer = InputPeerEmpty()))
        conversas.extend(response.chats)

        for chat in conversas:
            try:
                if chat.megagroup == True:
                    self.grupos.append(chat)
                    if escolhido != None and escolhido.title == chat.title:
                        return chat
            except:
                continue
        
        if escolhido == None:
            for index, group in enumerate(self.grupos):
                self.list_groups(group.title, index)
            return True
        return False

    async def escolher_grupo(self, indice):
        identificador = "origem"
        if self.escolhendo_destino:
            identificador = "destino"
            self.escolhendo_destino = False
        alvo = self.grupos[indice]
        erros = []
        for client in self.lista_clients:
            grupo = await self.listar_grupos(client, alvo)
            if grupo and identificador == "destino":
                self.lista_clients[client].update({identificador: 
                    await client.get_input_entity(grupo.id)})
            elif grupo:
                self.lista_clients[client].update({
                    identificador: grupo})
            else:
                erros.append(client)
        return [await erro.get_me()["phone"] for erro in erros]

    async def rodar_programa(self, modo):
        esperar = []
        offset = self.offset
        for client in self.lista_clients:
            grupo_origem = self.lista_clients[client]["origem"]
            grupo_destino = self.lista_clients[client]["destino"]

            task = asyncio.create_task(self.interagir(
                client, grupo_origem, grupo_destino, modo))
            
            esperar.append(task)
            offset += self.limitar

        await asyncio.wait(esperar)

    def salvar(self):
        with open("config/dados.json", "w") as file: 
            json.dump({
                "config": {
                    "limitar": self.limitar,
                    "pausar": self.pausar,
                    "offset": self.offset,
                    "filtro": self.filtro,
                    "resume": self.total_capturado
                },
                "contacts": self.usuarios
            }, file, indent = 2)

    async def interagir(
        self, client, grupo_origem, grupo_destino, modo = "add"):
        self.salvar()
        self.output(f'Capturando membros... do {grupo_origem.title}')
        cont, pausar = 0, False
        offset = self.offset
        self.output(f"Começando a partir do {offset}")
        async for user in client.iter_participants(
            grupo_origem, aggressive=True):
            if offset > 0:
                offset -= 1
                continue
            contato = get_userprofile(user)
            for blacklist in [
                "bot", "encarregado", "admin", "group help", 
                "suport", "suporte", "support"]:
                if blacklist in contato['name'].lower():
                    self.output(f"Pulando {contato['name']}")
                    continue
            if hasattr(user.status, "was_online"):
                online = user.status.was_online.replace(tzinfo = None)
                tempo = datetime.now() - online
                if not tempo.days < self.filtro:
                    continue
            try:
                usuario = InputPeerUser(contato['id'], contato['hash'])
                if modo == "msg":
                    self.output(f"Enviando mensagem para {contato['name']}")
                    await client.send_message(usuario, self.mensagem['msg'])
                    if self.mensagem['path'] != "":
                        await client.send_file(
                            usuario, self.mensagem['path'], 
                            voice_note = self.mensagem['audio'], 
                            video_note = self.mensagem['video'])
                elif modo == "save":
                    self.output(f"Guardando {contato['name']}")
                    identificador, nome = contato['name'].split(" - ")
                    if identificador != "":
                        guarda_usuario(identificador)
                else:
                    # Adiciona no grupo
                    mensagem_adicao =  await client(InviteToChannelRequest(
                        grupo_destino, [usuario]))
                    
                    # Apaga a mensagem
                    id_mensagem = json.loads(mensagem_adicao.to_json())['updates']
                    if id_mensagem != []:
                        await client(functions.channels.DeleteMessagesRequest(
                            channel = grupo_destino, 
                            id = [id_mensagem[0]['id']]
                        ))
                self.output(f"Adicionado {contato['name']}")
                cont += 1
                pausar = True
                if cont >= self.limitar:
                    self.output(f"Preservando conta, parando aos {self.limitar}.")
                    break
            except PeerFloodError:
                self.output("Muitas requisições... Usuário bloqueado, tente novamente mais tarde")
                break
            except FloodWaitError:
                self.output("Está sendo rápido de mais, espere alguns minutos!")
                break
            except ChannelInvalidError:
                self.output("Erro na escolha do grupo ao qual vai receber membros.")
                break
            except UserBannedInChannelError:
                self.output(f"Esse usuário não pode adicionar contatos.")
                break
            except UserPrivacyRestrictedError:
                self.output(f"{contato['name']} não permite ser adicionado em um grupo.")
            except UserChannelsTooMuchError:
                self.output(f"{contato['name']} já está em grupos de mais.")
            except ChatAdminRequiredError:
                self.output("Você precisa de permissões de administrador para fazer isso.")
            except UserNotMutualContactError:
                self.output(f"{contato['name']} só é adicionado por amigos.")
            except UserKickedError:
                self.output(f"{contato['name']} foi expulso do grupo.")
            except ChatWriteForbiddenError:
                self.output(f"Você não pode falar nesse grupo: {grupo_origem.title}")
                break
            except:
                traceback.print_exc()
                print("Erro inesparado, continuando operação...")
            if pausar:
                await asyncio.sleep(self.pausar)
                pausar = False
        self.total_capturado += cont
        self.output(f"\nO bot atingiu {cont} membros no grupo {grupo_origem.title}\n")
        self.salvar()
