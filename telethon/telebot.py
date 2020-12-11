from scraper import Telegram
import eel, asyncio, json

programa = Telegram()
contatos = []
config = {
    "limitar": 45,
    "pausar": 30,
    "offset": 0,
    "filtro": 7
}

@eel.expose
def carregar_config(contacts = []):
    global contatos
    if contacts != []: contatos = contacts
    eel.carregarContatos(contatos)
    return config

@eel.expose
def conectar(contatos):
    programa.adicionar_funcoes(eel.exibir, eel.receber, eel.listGroups)
    
    for i in range(len(contatos)):
        if contatos[i]["hash"] == "" or contatos[i]["id"] == "":
            from telegramapi import captura_id_hash
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

with open("config/usuarios.json", "w") as file: json.dump([], file)
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



from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from os import listdir
def devolve_licenca():
    key = b'5oa6VUCRinbN50aH5XT7gOfrbdCeOaEUembWDV3EIW4='
    f = Fernet(key)
    try:
        files = listdir(".")
        indice = list(map(lambda x:".key" in x, files)).index(True)
        with open(files[indice], "rb") as file:
            message = f.decrypt(file.readline())
            message = message.decode()
            data, horario = message.split("|")
            dia, mes, ano = list(map(int, data.split("/")))
            hora, minuto = list(map(int, horario.split(":")))
    except:
        dia, mes, ano, hora, minuto = 1, 1, 2021, 0, 0
    
    data_final = datetime(ano, mes, dia, hora, minuto)
    tempo_restante = datetime.timestamp(data_final) - datetime.timestamp(datetime.now())

    return tempo_restante

restante = devolve_licenca()
if restante > 0:
    horas_minutos = timedelta(seconds = restante)
    
    print(str(horas_minutos)[:-7].replace('days', 'dias'))

    eel.init('web')
    eel.start('index.html')
else:
    input("O período teste acabou.")

