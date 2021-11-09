from telegramapi import captura_id_hash
import eel, asyncio, json, requests, time
from datetime import timedelta
from scraper import Telegram

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

@eel.expose
def rodar_programa(modo):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        programa.rodar_programa(modo))

def autenticar_licenca(email):
    def devolve_restante(tempo_restante):
        if  tempo_restante < 0:
            validacao, mensagem = False, "Sua licença expirou."
        else:
            horas_minutos = timedelta(seconds = tempo_restante)
            duracao = str(horas_minutos)[:-7].replace('days', 'dias')
            if "dias" not in duracao:
                duracao += "h"
            mensagem = f"Sua licença dura {duracao}!"
            validacao = True
        return validacao, mensagem

    try:
        response = requests.get(
            "https://licenciador.vercel.app/api/clients/", 
            params = { "email": email, "botName": "telebot"
        }).json()
        if email in response:
            tempo_restante = response[email]["timestamp"] - time.time()
            validacao, mensagem = devolve_restante(tempo_restante)
        else:
            validacao, mensagem = False, "Compre uma licença!"
    except Exception as e:
        print(e)
        validacao, mensagem = False, "Servidor em manutenção!"
    return validacao, mensagem

@eel.expose
def login(email):
    global programa
    validacao, mensagem = autenticar_licenca(email)
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

eel.start('index.html', port = 8004)
