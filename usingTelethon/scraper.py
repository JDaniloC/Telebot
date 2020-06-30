from telethon.sync import TelegramClient
from telethon.errors import *
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty, InputPeerChannel, InputPeerUser
from telethon.tl.functions.channels import InviteToChannelRequest
import csv, json, time, sys, traceback, asyncio

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
        username = user.username
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

async def convida(client, grupo_alvo, entidade_principal, pausar):
    print(f'Capturando membros... do {grupo_alvo.title}')
    todos_membros = await client.get_participants(grupo_alvo, aggressive=True)
    
    cont = 0
    membros = []
    for user in todos_membros:
        user = get_userprofile(user)
        usuario = InputPeerUser(user['id'], user['hash'])
        print(f"Adicionando {user['name']} do grupo {grupo_alvo.title}")
        try:
            await client(InviteToChannelRequest(entidade_principal, [usuario]))
        except PeerFloodError:
            print("Muitas requisições... Usuário bloqueado, tente novamente mais tarde")
            break
        except UserPrivacyRestrictedError:
            print(f"{user['name']} não permite ser adicionado em um grupo.")
        except ChannelInvalidError:
            print("Erro na escolha do grupo ao qual vai receber membros")
            break
        except UserChannelsTooMuchError:
            print(f"{user['name']} já está em grupos de mais.")
        except:
            traceback.print_exc()
            print("Erro inesparado, continuando operação...")
            continue
        finally:
            if pausar:
                await asyncio.sleep(60)

async def main(usuarios, pausar = True):
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

    print("Escolha o grupo que vai receber os membros: ")
    grupo_principal = await captura_grupo(clients[0])

    # entidade_principal = InputPeerChannel(grupo_principal.id, grupo_principal.access_hash)
    lista_clients = {
        client: await client.get_input_entity(grupo_principal.id)
        for client in clients   
    }

    esperar = []
    
    print("\nEscolha um grupo para cada bot pegar membros:")
    for client in clients:
        grupo_alvo = await captura_grupo(client)

        entidade_principal = lista_clients[client]
        task = asyncio.create_task(convida(client, grupo_alvo, entidade_principal, pausar))
        
        esperar.append(task)

    await asyncio.wait(esperar)


if __name__ == "__main__":
    with open("dados.json") as dados:
        usuarios = json.load(dados)

    loop = asyncio.get_event_loop()

    loop.run_until_complete(main(usuarios))

    print("Programa finalizado.")