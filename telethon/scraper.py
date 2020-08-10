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

async def convida(client, grupo_alvo, entidade_principal, pausar, modo = "add", offset = 0):
    print(f'Capturando membros... do {grupo_alvo.title}')
    cont = 0
    pausar = False
    print("Começando a partir do", offset)
    async for user in client.iter_participants(grupo_alvo, aggressive=True):
        if offset > 0:
            offset -= 1
            continue
        user = get_userprofile(user)
        for blacklist in ["bot", "encarregado", "admin", "group help", "suport", "suporte", "support"]:
            if blacklist in user['name'].lower():
                print(f"Pulando {user['name']}")
                continue
        try:
            usuario = InputPeerUser(user['id'], user['hash'])
            if modo == "msg":
                print(f"Enviando mensagem para {user['name']}")
                await client.send_message(usuario, mensagem)
            elif modo == "save":
                print(f"Guardando {user['name']}")
                identificador, nome = user['name'].split(" - ")
                if identificador != "":
                    guarda_usuario(identificador)
            else:
                # print(f"Adicionando {user['name']} do grupo {grupo_alvo.title}", flush = True)
                await client(InviteToChannelRequest(entidade_principal, [usuario]))
            cont += 1
            pausar = True
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
            print(f"{user['name']} não permite ser adicionado em um grupo.")
        except UserChannelsTooMuchError:
            print(f"{user['name']} já está em grupos de mais.")
        except ChatAdminRequiredError:
            print("Você precisa de permissões de administrador para fazer isso.")
        except UserNotMutualContactError:
            print(f"{user['name']} só é adicionado por amigos.")
        except UserKickedError:
            print(f"{user['name']} foi expulso do grupo.")
        except:
            traceback.print_exc()
            print("Erro inesparado, continuando operação...")
        if pausar:
            await asyncio.sleep(pausar)
            pausar = False
    print(f"\nO bot atingiu {cont} membros no grupo {grupo_alvo.title}\n")

async def main(usuarios, pausar = 30, modo = "msg", offset = 0):
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
    elif modo == "msg":
        mensagem = input("Digite a mensagem: ")
        
    esperar = []
    
    print("\nEscolha um grupo para cada bot PEGAR membros:")
    for client in clients:
        grupo_alvo = await captura_grupo(client)

        if modo == "add":
            entidade_principal = lista_clients[client]
        else:
            entidade_principal = None
        task = asyncio.create_task(convida(client, grupo_alvo, entidade_principal, pausar, modo, offset))
        
        esperar.append(task)

        offset += 50

    await asyncio.wait(esperar)


if __name__ == "__main__":
    with open("dados.json") as dados:
        usuarios = json.load(dados)

    loop = asyncio.get_event_loop()

    loop.run_until_complete(main(usuarios))

    print("Programa finalizado.")