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
from amanobot.exception import (
    BotWasBlockedError, BotWasKickedError)
from amanobot.namedtuple import (InlineKeyboardMarkup, InlineKeyboardButton,
 ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove)


bot_name = "🏁 -- ==W.S SINA'S== -- 🏁"

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
        par = re.search(
            r'[A-Za-z]{6}(-OTC)?', texto.replace("/", ""))[0]
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
        self.listas_de_entradas[atual]['id'] = {}
        for canal in self.channel:    
            try:
                mensagem = self.bot.sendMessage(
                    canal, f"{bot_name}\nTransmissão iniciada\nNão delete essa mensagem.")
            except (BotWasBlockedError, BotWasKickedError):
                self.channel.remove(canal)
                mensagem = None
            except Exception as e:
                print(e)
                self.bot = amanobot.Bot(self.token)
                mensagem = self.bot.sendMessage(
                    canal, f"{bot_name}\nTransmissão iniciada\nNão delete essa mensagem.")
            
            self.listas_de_entradas[atual]['id'][canal] = (
                canal, mensagem['message_id'])
        
        # Resultados
        self.listas_de_entradas[atual]["win"] = 0
        self.listas_de_entradas[atual]["loss"] = 0
        self.listas_de_entradas[atual]["winsg"] = 0
        self.listas_de_entradas[atual]["closed"] = 0
        self.listas_de_entradas[atual]['result'] = ""
        hora_parcial = time.time()

        lista_entradas = self.listas_de_entradas[atual]['lista']
        keys = list(lista_entradas.keys())
        for key in keys:
            if self.listas_de_entradas[atual]['on'] and self.esperarAte(
                chat_id, key):
                if self.listas_de_entradas[atual]['on']:
                    i = 0
                    while i < len(self.channel):
                        print(self.channel, i)
                        try:
                            mensagem = self.bot.sendMessage(
                                self.channel[i], 
                                lista_entradas[key]['msg'])
                            par = lista_entradas[key]['par']
                            hora = lista_entradas[key]['hora']
                            direcao = lista_entradas[key]['direcao']
                            timeframe = lista_entradas[key]['periodo']
                            gales = lista_entradas[key]['gale']
                            apagar = keys[-1] == key
                            threading.Thread(
                                target=self.mandar_resultado,
                                args = ((self.channel[i], 
                                    mensagem['message_id']), 
                                    par, hora, timeframe, 
                                    direcao, gales,
                                    atual, apagar)).start()
                            if (
                            time.time() - hora_parcial > (3600 * 3) and
                            len(self.channel) > 0):
                                hora_parcial = time.time()
                                self.mandar_parcial(
                                    self.channel[i], atual)
                                self.mandar_completa(atual)
                            i += 1
                        except (BotWasBlockedError, 
                                BotWasKickedError):
                            self.channel.remove(
                                self.channel[i])
                        except Exception as e:
                            print(e)
                            self.bot = amanobot.Bot(self.token)
                            time.sleep(1)
        
        for canal in self.channel:
            self.mandar_parcial(canal, atual)

        if not self.listas_de_entradas[atual]['on']:
            del self.listas_de_entradas[atual]

        self.bot.sendMessage(chat_id, "Transmissão finalizada")
        print("Terminou a transmissão")

    def mandar_completa(self, atual):
        win = self.listas_de_entradas[atual]["win"]
        loss = self.listas_de_entradas[atual]["loss"]
        timeframe = self.listas_de_entradas[atual]['timeframe']
        gales = self.listas_de_entradas[atual]['gales']
        result = self.listas_de_entradas[atual]['result']
        assertividade = win / (win + loss) * 100 if win + loss > 0 else 100
        resposta = f"""🚀 Resultado do dia 🚀
        {timeframe} {gales}

{result}

🎯 Assertividade: {round(assertividade, 2)}%"""
        for canal in self.channel:
            message_id = self.listas_de_entradas[atual]['id'][canal]
            try:
                self.bot.editMessageText(message_id, resposta)
            except Exception as e:
                if "modified" not in str(e):
                    self.bot = amanobot.Bot(self.token)
                    self.bot.editMessageText(message_id, resposta)

    def mandar_parcial(self, canal, atual):
        win = self.listas_de_entradas[atual]["win"]
        loss = self.listas_de_entradas[atual]["loss"]
        winsg = self.listas_de_entradas[atual]["winsg"]
        gales = self.listas_de_entradas[atual]["gales"]
        timeframe = self.listas_de_entradas[atual]["timeframe"]
        fechados = self.listas_de_entradas[atual]["closed"]
        if win > 0 or loss > 0:
            mensagem_parcial = f'''{bot_name}
Lista {gales} {timeframe}

✅ Vitórias {win}
🔒 Fechados {fechados}
❌ Derrotas {loss}

✅ Sem gale: {winsg}
🐔 Win Gale: {win - winsg}

🎯 Assertividade: {round(win / (win + loss) * 100, 2)}%
                        '''
            try:
                self.bot.sendMessage(canal, mensagem_parcial)
            except:
                self.bot = amanobot.Bot(self.token)
                self.bot.sendMessage(canal, mensagem_parcial)

    def mandar_resultado(
        self, message_id, paridade, hora_entrada, 
        timeframe, direcao, max_gales, atual, apagar):
        time.sleep(300)
        timeframe *= 60
        espera = datetime.now().timestamp() + (timeframe * 3) + 5

        abertas = self.IQ.get_all_open_time()
        esta_aberto = True
        abertas_digital = [x for x in abertas['digital'] 
                            if abertas['digital'][x]['open']]
        if timeframe == 60:
            esta_aberto = (
                paridade in abertas_digital or paridade in 
                [x for x in abertas['turbo'] 
                if abertas['turbo'][x]['open']])
        else:
            esta_aberto = (
                paridade in abertas_digital or paridade in
                [x for x in abertas['binary'] 
                if abertas['binary'][x]['open']])

        gales = 0
        win = False
        texto_gales = f"🐔 Até {max_gales[0]} gales" if len(max_gales) == 1 else ""
        if esta_aberto:
            time.sleep(espera - time.time())

            velas = self.IQ.get_candles(
                paridade, timeframe, 4, time.time())
            velas = [
                1 if x['close'] - x['open'] > 0 else 
                0 if x['close'] - x['open'] == 0 else 
                -1 for x in velas
            ]
            
            while gales < 3 and not win:
                win = velas[gales] == 1 if direcao == "call" else velas[gales] == -1
                if not win:
                    gales += 1

        if len(max_gales) == 1 and gales == 2 and max_gales[0] == 1:
            win = False

        ordem = '⬆' if direcao.lower() == "call" else '⬇'
        resultado = '🔒' if not esta_aberto else (gales * '🐔') + '✅' if win else '❌'

        resposta = f"""
{bot_name}
📊 Ativo: {paridade}
⏰ Período: M{timeframe // 60}
⏱ Horário: {hora_entrada}
{ordem} Direção: {direcao.upper()}
{texto_gales}
Resultado: {resultado}
        """
        try:
            # Salva informações
            self.listas_de_entradas[atual]['result'] += (
                f"{hora_entrada} {paridade} {direcao.upper()} {resultado}\n")
            if win:
                self.listas_de_entradas[atual]['win'] += 1
                if gales == 0:
                    self.listas_de_entradas[atual]["winsg"] += 1
            elif esta_aberto:
                self.listas_de_entradas[atual]["loss"] += 1
            else:
                self.listas_de_entradas[atual]["closed"] += 1

            self.mandar_completa(atual)
        except Exception as e:
            print(type(e), e)

        try:
            self.bot.editMessageText(message_id, resposta)
        except:
            self.bot = amanobot.Bot(self.token)
            self.bot.editMessageText(message_id, resposta)
        
        if apagar:
            for canal in self.channel:
                self.mandar_parcial(canal, atual)
            del self.listas_de_entradas[atual]

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
{bot_name}
🔰 ENTRADA {hora}
⏱ Período: {periodo}
📊 Ativo: {par}
{"⬆" if direcao.lower() == "call" else "⬇"} Direção: {direcao.upper()}
{tipo}
                '''
                resultado[key]['par'] = par
                resultado[key]['hora'] = hora
                resultado[key]['gale'] = [
                    int(x) for x in tipo.split() if x.isdigit()]
                resultado[key]['direcao'] = direcao.lower()
                resultado[key]['periodo'] = int(periodo.strip("M"))
                resultado[key]['result'] = "?"
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
                if not options['deleted']:
                    resposta = ""
                    for entrada in options['lista'].values():
                        resposta += entrada['msg']
                    self.bot.sendMessage(
                        from_id, resposta)
            self.bot.sendMessage(from_id, "Fim das listas.")
        elif query_data == "start":
            print("Entranho no modo de transmissão")
            self.bot.answerCallbackQuery(
                query_id, text = "Modo enviar lista")
            opcoes = []
            for key, value in self.listas_de_entradas.items():
                if not value['on'] and not value['deleted']:
                    opcoes.append(
                        str(key) + " - " + value['nome'])
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
                if value['on'] and not value['deleted']:
                    opcoes.append(
                        str(key) + " - " + value['nome'])
                    value['deleted'] = True

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
            if "1 gal" in entrada.lower():
                return "🐔 Até 1 gale"
            elif "2 gal" in entrada.lower():
                return "🐔 Até 2 gales"
        return ""

    def pegar_periodo(self, lista):
        for entrada in lista:
            if "M15" in entrada:
                return "M15"
            elif "M5" in entrada:
                return "M5"
            elif "M1" in entrada:
                return "M1"
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
                        "gales": tipo,
                        "timeframe": periodo,
                        "lista": self.formatar_entradas(
                            tipo, periodo, entradas),
                        "deleted": False
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
                pprint.pprint(self.channel)
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