try:
    import telethon
except:
    print("Instalando dependência...")
    from subprocess import call
    call(['pip', 'install', 'telethon'])
from telethon.sync import TelegramClient
from telethon.errors import *
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty, InputPeerChannel, InputPeerUser
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.contacts import AddContactRequest, DeleteContactsRequest
import json, time, sys, traceback, asyncio

async def captura_grupo(client):
    '''
    Captura um grupo da lista de conversas do client
    '''
    conversas = []
    ultima_data = None
    maximo_conversas = 200
    grupos = []

    response = await client(GetDialogsRequest(
                offset_date = ultima_data,
                offset_id = 0,
                offset_peer = InputPeerEmpty(),
                limit = maximo_conversas,
                hash = 0
            ))
    conversas.extend(response.chats)

    for chat in conversas:
        try:
            if chat.megagroup == True:
                grupos.append(chat)
        except:
            continue

    print('\nLista de grupos:')
    for index, group in enumerate(grupos):
        print(str(index) + ' - ' + group.title)
    grupo_alvo = grupos[int(input("Digite o número correspondente: "))]

    return grupo_alvo


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
    with open("usuarios.json", "r+", encoding = "utf-8") as file:
        lista = json.load(file)
    lista.append(info)
    with open("usuarios.json", "w", encoding = "utf-8") as file:
        json.dump(lista, file, indent = 2)

total_capturado = 0

async def interagir(
    client, grupo_alvo, entidade_principal, tempo_pausa, 
    modo = "add", offset = 0, mensagem = {}, limitar = False):
    global total_capturado
    print(f'Capturando membros... do {grupo_alvo.title}')
    cont = 0
    pausar = False
    print("Começando a partir do", offset)
    async for user in client.iter_participants(grupo_alvo, aggressive=True):
        if offset > 0:
            offset -= 1
            continue
        contato = get_userprofile(user)
        for blacklist in [
            "bot", "encarregado", "admin", "group help", 
            "suport", "suporte", "support"]:
            if blacklist in contato['name'].lower():
                print(f"Pulando {contato['name']}")
                continue
        try:
            usuario = InputPeerUser(contato['id'], contato['hash'])
            if modo == "msg":
                print(f"Enviando mensagem para {contato['name']}")
                await client.send_message(usuario, mensagem['msg'])
                if mensagem['path'] != "":
                    await client.send_file(
                        usuario, mensagem['path'], 
                        voice_note = mensagem['audio'])
            elif modo == "save":
                print(f"Guardando {contato['name']}")
                identificador, nome = contato['name'].split(" - ")
                if identificador != "":
                    guarda_usuario(identificador)
            else:
                print(f"Adicionando {contato['name']} do grupo {grupo_alvo.title}")
                username = user.username
                number = user.phone 
                first_name = user.first_name
                last_name = user.last_name
                # Adiciona nos contatos
                await client(AddContactRequest(
                    user.id, number if number != None else "",
                    first_name if first_name != None else "", 
                    last_name if last_name != None else ""))
                await asyncio.sleep(1)
                
                # Adiciona no grupo
                await client(InviteToChannelRequest(entidade_principal, [usuario]))
                await asyncio.sleep(1)
                
                # Exclui dos contatos
                for x in [username, first_name, last_name, number, user.id]:
                    if x != None:
                        try:
                            result = await client(DeleteContactsRequest([x]))
                            break
                        except:
                            pass
            cont += 1
            pausar = True
            if limitar and cont >= 100:
                print("Preservando conta, parando aos 40.")
                break
        except PeerFloodError:
            print("Muitas requisições... Usuário bloqueado, tente novamente mais tarde")
            break
        except FloodWaitError:
            print("Está sendo rápido de mais, espere alguns minutos!")
            break
        except ChannelInvalidError:
            print("Erro na escolha do grupo ao qual vai receber membros.")
            break
        except UserPrivacyRestrictedError:
            print(f"{contato['name']} não permite ser adicionado em um grupo.")
        except UserChannelsTooMuchError:
            print(f"{contato['name']} já está em grupos de mais.")
        except ChatAdminRequiredError:
            print("Você precisa de permissões de administrador para fazer isso.")
        except UserNotMutualContactError:
            print(f"{contato['name']} só é adicionado por amigos.")
        except UserKickedError:
            print(f"{contato['name']} foi expulso do grupo.")
        except:
            traceback.print_exc()
            print("Erro inesparado, continuando operação...")
        if pausar:
            await asyncio.sleep(tempo_pausa)
            pausar = False
    total_capturado += cont
    print(f"\nO bot atingiu {cont} membros no grupo {grupo_alvo.title}\n")

async def main(
    usuarios, pausar = 30, modo = "msg", 
    offset = 0, mensagem = "", limitar = False):
    global total_capturado
    
    with open("usuarios.json", "w") as file:
        json.dump([], file)
    clients = []

    # # Conexão # #
    for user in usuarios:
        api_id = user['id']
        api_hash = user['hash']
        numero_celular = user['number']

        client = TelegramClient(numero_celular, api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            print(f"{numero_celular} não conseguiu conectar, enviando código.")
            await client.send_code_request(numero_celular)
            try:
                await client.sign_in(numero_celular, input("Coloque o código: "))
                clients.append(client)
            except PhoneCodeExpiredError:
                print("Você demorou de mais pra colocar o código")
            except PhoneCodeInvalidError:
                print("Código errado!")
        else:
            print(f"{numero_celular} conectado com sucesso.")
            clients.append(client)

    lista_clients = {}
    if modo == "add":
        for client in clients:
            print("Escolha o grupo que vai RECEBER os membros: ")
            grupo_principal = await captura_grupo(client)

            lista_clients.update({
                client: await client.get_input_entity(grupo_principal.id)
            })
        
    esperar = []
    
    print("\nEscolha um grupo para cada bot PEGAR membros:")
    for client in clients:
        grupo_alvo = await captura_grupo(client)

        if modo == "add":
            entidade_principal = lista_clients[client]
        else:
            entidade_principal = None
        task = asyncio.create_task(interagir(
            client, grupo_alvo, entidade_principal, 
            pausar, modo, offset, mensagem, limitar))
        
        esperar.append(task)

        offset += 50

    await asyncio.wait(esperar)
    print(f"Interagiu com um total de {total_capturado}")


if __name__ == "__main__":
    with open("dados.json") as dados:
        usuarios = json.load(dados)

    loop = asyncio.get_event_loop()

    loop.run_until_complete(main(usuarios))

    print("Programa finalizado.")