import eel, asyncio, json, requests, time, sys, traceback
from googleapi import get_google_credentials
from telegramapi import captura_id_hash
from datetime import timedelta
from scraper import Telegram
import os

DISABLE_AUTH = os.environ.get('TELEBOT2_DISABLE_AUTH', '0') == '1'
DISABLE_OAUTH = os.environ.get('TELEBOT2_DISABLE_OAUTH', '0') == '1'

programa = None
eel.init('web')

contatos = []
config = {
    "limitar": 45,
    "pausar": 30,
    "offset": 0,
    "filtro": 7,
    "resume": 0
}

def exibir(*args): eel.exibir(*args)
def listGroups(*args): eel.listGroups(*args)

@eel.expose
def carregar_config(contacts = []):
    global contatos
    if contacts != []: contatos = contacts
    eel.carregarContatos(contatos)
    return config

@eel.expose
def conectar(contatos):
    programa.adicionar_funcoes(exibir, eel.perguntar, listGroups)
    
    for i in range(len(contatos)):
        if contatos[i]["hash"] == "" or contatos[i]["id"] == "":
            contatos[i] = captura_id_hash(contatos[i]["number"])
    carregar_config(contatos)
    programa.usuarios = contatos
    
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(
        programa.conectar())
    return result
@eel.expose
def modificar_config(config):
    programa.pausar   = int(config["pausar"])
    programa.limitar  = int(config["limitar"])
    programa.offset   = int(config["offset"])
    programa.filtro   = int(config["filtro"])
    programa.mensagem = config["mensagem"]

@eel.expose
def listar_grupos(destino = False):
    if destino:
        programa.escolhendo_destino = True
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        programa.listar_grupos())

@eel.expose
def escolher_grupo(indice):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        programa.escolher_grupo(int(indice)))

async def criar_tasks(modo):
    esperar = []
    offset = programa.offset
    for client in programa.lista_clients:
        grupo_origem = programa.lista_clients[client]["origem"]
        grupo_destino = programa.lista_clients[client]["destino"]
        exibir(f"Coletando usuários do grupo {grupo_origem.title}...")
        users = await client.get_participants(grupo_origem, aggressive = True)
        exibir(f"Consegui coletar {len(users)} usuários do grupo {grupo_origem.title}.")
        task = asyncio.create_task(programa.interagir(
            client, grupo_origem, grupo_destino, users, modo))
        
        esperar.append(task)
        offset += programa.limitar

    await asyncio.wait(esperar)

@eel.expose
def rodar_programa(modo):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(criar_tasks(modo))


def autenticar_licenca():
    if DISABLE_AUTH:
        return True, "License check disabled for development."

    def devolve_restante(tempo_restante):
        if tempo_restante < 0:
            validacao, mensagem = False, "Your license has expired."
        else:
            horas_minutos = timedelta(seconds=tempo_restante)
            duracao = str(horas_minutos)[:-7].replace('days', 'days')
            if "days" not in duracao:
                duracao += "h"
            mensagem = f"Welcome, your license is valid for {duracao}!"
            validacao = True
        return validacao, mensagem

    if DISABLE_OAUTH:
        email = "anon@oauth.local"
    else:
        try:
            _, email, _ = get_google_credentials()
        except Exception as e:
            arquivo = open("config/errors.log", "a",
                encoding = "utf-8", errors = "??")
            traceback.print_exc(file = arquivo)
            return False, "Não foi possível obter suas credenciais."

    try:
        response = requests.get(
            "https://licenciador.vercel.app/api/clients/",
            params={"email": email, "botName": "telebot"}
        ).json()
        if email in response:
            tempo_restante = response[email]["timestamp"] - time.time()
            validacao, mensagem = devolve_restante(tempo_restante)
        else:
            validacao, mensagem = False, "Buy a license!"
    except Exception as e:
        print(e)
        validacao, mensagem = False, "Server under maintenance!"
    return validacao, mensagem

@eel.expose
def login():
    global programa
    validacao, mensagem = autenticar_licenca()
    if validacao:
        try:
            programa = Telegram()

            with open("config/usuarios.json", "w"
                ) as file: json.dump([], file)
            try:
                with open("config/dados.json", "r+") as file:
                    dados = json.load(file)
                for dado in dados["contacts"]:
                    contatos.append({
                        "id":     dado["id"],
                        "hash":   dado["hash"],
                        "number": dado["number"]
                    })
                config = dados["config"]
                config["mensagem"] = {
                    "msg": "", "path": "", "audio": False }
                modificar_config(config)
            except Exception as e: print(e)

        except Exception as e:
            print(e)
            return False, "Verifique suas credenciais!"
        return True, mensagem
    return False, mensagem


def quit(*args): sys.exit()

eel.start('index.html', port = 8004, close_callback = quit)
