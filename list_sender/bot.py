try:
    import amanobot
except ModuleNotFoundError:
    from subprocess import call
    call(["pip", "install", "amanobot"])
    import amanobot

from iqoptionapi.stable_api import IQ_Option
import time, pprint, traceback, json, re, threading, sys
from datetime import datetime, timedelta
from amanobot.loop import MessageLoop
from amanobot.namedtuple import (InlineKeyboardMarkup, InlineKeyboardButton,
 ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove)

def escreve_erros(erro):
    '''
    Guarda o traceback do erro em um arquivo.log
    '''
    linhas = " -> ".join(re.findall(r'line \d+', str(traceback.extract_tb(erro.__traceback__))))
    with open("errors.log", "a") as file:
        file.write(f"{type(erro)} - {erro}:\n{linhas}\n")

def pegar_comando(texto):
    '''
    Recebe um texto e devolve:
    {
        "data": [dia, mes, ano],
        "hora": [hora, minuto]
        "par": par,
        "ordem": ordem
    }
    No qual o conteúdo das listas são inteiros
    '''
    try:
        data = re.search(r'\d{2}\W\d{2}\W\d{4}', texto)
        if data:
            data = [int(x) for x in re.split(r"\W", data[0])]
        else:
            hoje = datetime.fromtimestamp(datetime.utcnow().timestamp() - 10800)
            data = [hoje.day, hoje.month, hoje.year]
        hora = re.search(r'\d{2}:\d{2}', texto)[0]
        hora = [int(x) for x in re.split(r'\W', hora)]
        par = re.search(r'[A-Za-z]{6}', texto.replace("/", ""))[0]
        ordem = re.search(r'CALL|PUT|call|put', texto)[0].lower()
    except:
        print(f"Não entendi a entrada {texto}")
        return None

    comando = {
        "data": data,
        "hora": hora,
        "par": par,
        "ordem": ordem
    }

    return comando

def strDateHour(number):
    '''
    Converte números de 1 dígito para 2 dígitos:
        0:0 -> 00:00
        2/1/2000 -> 02/01/2000
    params:
        number = tipo int
    return:
        string do resultado
    '''
    return str(number) if len(str(number)) != 1 else "0" + str(number)

class Telegram:
    def __init__(self, token, channel, meu_id):
        self.token = token
        self.bot = amanobot.Bot(token)
        self.my_id = self.bot.getMe()['id']
        self.listas_de_entradas = {}
        self.channel = channel
        self.meu_id = meu_id
        
        self.IQ = IQ_Option("hiyivo1180@tmail7.com", "senha123")
        self.IQ.connect()

        self.rodando = True
        self.escolher_lista = False
        self.esperar_lista = False
        self.parar_transmissao = False
        self.lista_atual = 1

        MessageLoop(self.bot, {
            "chat": self.recebe_comandos,
            "callback_query": self.resposta_botao
        }).run_as_thread()

        print("Esperando comandos...")
        while self.rodando:
            time.sleep(10)
            print(str(datetime.now())[:-7], end = "\r")

    def esperarAte(self, identificador, data_hora):
        '''
        Espera até determinada data/hora:minuto
        Recebe um dia/hora:minuto
        '''
        indice, dia, horario = data_hora.split("/")
        horas, minutos = map(int, horario.split(":"))
        
        data = datetime.now()
        alvo = datetime.fromtimestamp(
            data.replace(
            day = int(dia), 
            hour = horas, 
            minute = minutos, 
            second = 0, 
            microsecond = 0).timestamp() - 300) # -5min 
        agora = datetime.utcnow().timestamp() - 10800 # -3Horas
        segundos = alvo.timestamp() - agora
        if segundos > 0:
            print(f"Esperando até as {alvo}")
            self.bot.sendMessage(identificador, f"\n [...] Próxima entrada será às {alvo} [...]")
            time.sleep(segundos)
            return True
        elif segundos > -60:
            return True
        return False

    def transmissao(self, chat_id, atual):
        '''
        Função que percorre a lista de entradas e envia para o canal
        '''
        print("Começando a transmitir")
        lista_entradas = self.listas_de_entradas[atual]['lista']
        keys = list(lista_entradas.keys())
        indice = 0
        while indice < len(keys):
            key = keys[indice]
            if self.listas_de_entradas[atual]['on'] and self.esperarAte(chat_id, key):
                if self.listas_de_entradas[atual]['on']:
                    for canal in self.channel:
                        try:
                            self.bot.sendMessage(
                                canal, lista_entradas[key]['msg'])
                            
                            par =lista_entradas[key]['par']
                            direcao = lista_entradas[key]['direcao']
                            timeframe = lista_entradas[key]['periodo']
                            threading.Thread(
                                target=self.mandar_resultado,
                                args = (chat_id, par, 
                                timeframe, direcao)).start()
                        except Exception as e:
                            self.bot = amanobot.Bot(self.token)
                            indice -= 1
                            time.sleep(1)
            indice += 1
        del self.listas_de_entradas[atual]
        self.bot.sendMessage(chat_id, "Transmissão finalizada")
        print("Terminou a transmissão")

    def mandar_resultado(
        self, chat_id, paridade, timeframe, direcao):
        timeframe *= 60
        time.sleep((timeframe * 4) + 300)

        velas = self.IQ.get_candles(
            paridade, timeframe, 4, time.time())
        velas = [
            1 if x['close'] - x['open'] > 0 else 
            0 if x['close'] - x['open'] == 0 else 
            -1 for x in velas
        ]
        print(datetime.now(), velas)

        win = False
        gales = 0
        while gales < 3 and not win:
            win = velas[gales] == 1 if direcao == "call" else velas[gales] == -1
            if not win:
                gales += 1
        
        resposta = f"""
📊 Par: {paridade}
{'⬆' if direcao.lower() == "call" else '⬇'} Direção: {direcao}
⏰ Tempo: {timeframe // 60}
Resultado: {(gales * 'G') + '✅' if win else '❌'}
        """
        try:
            self.bot.sendMessage(chat_id, resposta)
        except:
            self.bot = amanobot.Bot(self.token)
            self.bot.sendMessage(chat_id, resposta)

    def formatar_entradas(self, tipo, periodo, comandos):
        '''
        Recebe uma lista de comandos, e formata do jeito correto.
        '''
        resultado = {}
        for indice, comando in enumerate(comandos):
            try:
                comando = pegar_comando(comando)
                if comando == None:
                    continue
                dia, mes, ano = comando['data']
                data = "/".join(
                    list(map(strDateHour, comando["data"])))
                hora = ":".join(
                    list(map(strDateHour, comando["hora"])))
                par = comando['par']
                direcao = comando['ordem']
                key = str(indice)+"/"+str(dia)+"/"+hora
                resultado[key] = {}
                resultado[key]['msg'] = f'''
🎯 M.M_007 Bot 🎯
🔰 ENTRADA {hora}
⏱ Período: {periodo}
📊 Ativo: {par}
{"⬆" if direcao.lower() == "call" else "⬇"} Direção: {direcao.upper()}
{tipo}
                '''
                resultado[key]['par'] = par
                resultado[key]['direcao'] = direcao.lower()
                resultado[key]['periodo'] = int(periodo.strip("M"))
            except Exception as e:
                print("Não entendi a entrada:", comando)
        return resultado

    def mostrar_comandos(self, comando):
        '''
        Função que mostra os botões do menu
        Chamada quando fala /comandos
        '''
        nome = comando["from"]["first_name"] + " " + comando["from"]["last_name"]

        keyboard = InlineKeyboardMarkup(inline_keyboard = [
            [InlineKeyboardButton(
                text = "Registrar nova lista", 
                callback_data = "newlist"
            )],
            [InlineKeyboardButton(
                text = "Ver lista registrada", 
                callback_data = "showlist"
            )],
            [InlineKeyboardButton(
                text = "Começar transmissão", 
                callback_data = "start"
            )],
            [InlineKeyboardButton(
                text = "Parar transmissão",
                callback_data = "stop"
            )],
            [InlineKeyboardButton(
                text = "Desligar bot", 
                callback_data = "desligar",
            )]
        ])

        self.bot.sendMessage(
            comando["chat"]["id"], 
            f"Olá {nome}, o que você deseja?",
            reply_markup = keyboard
        )

    def resposta_botao(self, comando):
        '''
        Função que recebe os comandos dos botões
        '''

        query_id, from_id, query_data = amanobot.glance(comando, flavor = "callback_query")

        if query_data == "newlist":
            print("Entrando no modo de recebimento")
            self.bot.answerCallbackQuery(
                query_id, text = "Modo receber nova lista.")
            self.bot.sendMessage(
                from_id, """Me envie a próxima lista. 
    Formato da lista:
        Sinais (1/2) gale M(1/5/15/30)
        01/07/2020 00:05 EURUSD PUT
        01/07/2020 01:00 USDJPY CALL
        """
            )
            self.esperar_lista = True
        elif query_data == "showlist":
            print("Entrando no modo de mostragem")
            self.bot.answerCallbackQuery(
                query_id, text = "Modo mostrar lista")

            for options in self.listas_de_entradas.values():
                self.bot.sendMessage(
                    from_id, "\n".join(options['lista'].values()))
            self.bot.sendMessage(from_id, "Fim das listas.")
        elif query_data == "start":
            print("Entranho no modo de transmissão")
            self.bot.answerCallbackQuery(
                query_id, text = "Modo enviar lista")

            opcoes = []
            for key, value in self.listas_de_entradas.items():
                if not value['on']:
                    opcoes.append(str(key) + " - " + value['nome'])
            botoes = []
            for opcao in opcoes:
                botoes.append([KeyboardButton( text = opcao )])
            if len(botoes) > 0:
                self.escolher_lista = True
                self.bot.sendMessage(from_id, "Qual lista?", 
                    reply_markup = ReplyKeyboardMarkup( keyboard = botoes))
            else:
                self.bot.sendMessage(from_id, "Nenhuma lista registrada")
            
        elif query_data == "stop":
            opcoes = []
            for key, value in self.listas_de_entradas.items():
                if value['on']:
                    opcoes.append(str(key) + " - " + value['nome'])
            botoes = []
            for opcao in opcoes:
                botoes.append([KeyboardButton( text = opcao )])
            if len(botoes) > 0:
                self.parar_transmissao = True
                self.bot.sendMessage(from_id, "Qual lista?", 
                    reply_markup = ReplyKeyboardMarkup( keyboard = botoes))
            else:
                self.bot.sendMessage(from_id, "Nenhuma transmissão ativa")
        elif query_data == "desligar":
            self.bot.answerCallbackQuery(
                query_id, "Bot desligado.")
            self.bot.sendMessage(from_id, "Bot desligado")
            self.rodando = False

    def pegar_gales(self, lista):
        for entrada in lista:
            if "1 gal" in entrada:
                return "🐔 Até 1 gale"
            elif "2 gal" in entrada:
                return "🐔 Até 2 gales"
        return ""

    def pegar_periodo(self, lista):
        for entrada in lista:
            if "M1" in entrada:
                return "M1"
            elif "M5" in entrada:
                return "M5"
            elif "M15" in entrada:
                return "M15"
            elif "M30" in entrada:
                return "M30"
        return "M5"

    def recebe_comandos(self, comando):
        '''
        Função que é chamada caso falar no chat
        '''

        if comando != []:
            content_type, chat_type, chat_id = amanobot.glance(comando)

            if chat_id in self.meu_id:
                if self.escolher_lista:
                    key, nome = comando['text'].split(" - ")
                    key = int(key)
                    if self.listas_de_entradas.get(key):
                        mensagem = "Lista já iniciada"
                        if not self.listas_de_entradas[key]['on']:
                            self.listas_de_entradas[key]['on'] = True
                            threading.Thread(
                                target = self.transmissao, 
                                args = (chat_id, key)
                            ).start()
                            mensagem = "Transmissão iniciada"
                        self.bot.sendMessage(chat_id, mensagem,
                            reply_markup = ReplyKeyboardRemove())
                    self.escolher_lista = False
                elif self.esperar_lista:
                    pprint.pprint(comando['text'])
                    entradas = comando.get('text').split("\n")
                    tipo = self.pegar_gales(entradas)
                    periodo = self.pegar_periodo(entradas)
                    self.lista_atual += 1
                    self.listas_de_entradas[self.lista_atual] = {
                        "on": False,
                        "nome": f"{tipo}|{periodo}",
                        "lista": self.formatar_entradas(
                            tipo, periodo, entradas)
                    }
                    self.esperar_lista = False
                    self.bot.sendMessage(chat_id, "Lista salva")
                elif self.parar_transmissao:
                    try:
                        key, nome = comando['text'].split(" - ")
                        self.listas_de_entradas[int(key)]['on'] = False
                        self.bot.sendMessage(
                            chat_id, "Transmissão cancelada", 
                            reply_markup = ReplyKeyboardRemove())
                    except:
                        self.bot.sendMessage(chat_id, 
                            "Não consegui parar a transmissão", 
                            reply_markup = ReplyKeyboardRemove())
                    self.parar_transmissao = False
                elif comando.get('text') in [
                    "/comandos", 
                    "/start"]:
                    self.mostrar_comandos(comando)
            elif comando['chat'].get("type") in [
                "group", "supergroup", "channel"]:
                adicionar = comando.get('new_chat_participant')
                remover = comando.get('left_chat_participant')
                if adicionar:
                    adicionar = adicionar.get('id') == self.my_id
                elif remover:
                    remover = remover.get('id') == self.my_id
                if adicionar and comando['chat']['id'] not in self.channel:
                    self.channel.append(comando['chat']['id'])
                elif remover and comando['chat']['id'] in self.channel:
                    self.channel.remove(comando['chat']['id'])
            else:
                pprint.pprint(comando)

if __name__ == "__main__":
    dia, mes, ano, hora, minuto = 30, 8, 2020, 1, 10

    data_final = datetime(ano, mes, dia, hora, minuto)
    tempo_restante = datetime.timestamp(data_final) - datetime.timestamp(datetime.now())

    if  tempo_restante < 0:
        input("Acabou o tempo teste. Digite enter para fechar o programa.")
        sys.exit(0)
    else:
        restante = data_final - datetime.now()
        horas_minutos = timedelta(seconds = tempo_restante)
        duracao = str(horas_minutos)[:-7].replace('days', 'dias')
        if "dias" not in duracao:
            duracao += "h"
        print(f"O período teste dura {duracao}")

    verificador = True
    try:
        with open("settings.json", "r+") as file:
            info = json.load(file)
        program = Telegram(info["token"], info["canal"], info["id"])
        verificador = program.rodando
        with open("settings.json", "w") as file:
            info['canal'] = program.channel
            json.dump(info, file, indent = 2)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print("Aconteceu um problema, se persistir chame o técnico")
        escreve_erros(e)
    if verificador:
        input("Digite Enter para fechar")