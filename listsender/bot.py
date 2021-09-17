from datetime import datetime
from amanobot.loop import MessageLoop
from iqoptionapi.stable_api import IQ_Option
import time, pprint, traceback, json, re, threading, sys, amanobot
from amanobot.exception import BotWasBlockedError, BotWasKickedError
from amanobot.namedtuple import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove)

sys.path.append(".")

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
        "ordem": ordem,
        "timeframe": int
    }
    No qual o conteúdo das listas são inteiros
    '''
    try:
        data = re.search(r'\d{2}\W\d{2}\W\d{4}', texto)
        if data:
            data = [int(x) for x in re.split(r"\W", data[0])]
        else:
            hoje = datetime.fromtimestamp(
                datetime.utcnow().timestamp() - 10800)
            data = [hoje.day, hoje.month, hoje.year]
        hora = re.search(r'\d{2}:\d{2}', texto)[0]
        hora = [int(x) for x in re.split(r'\W', hora)]
        par = re.search(
        r'[A-Za-z]{6}(-OTC)?', texto.upper().replace("/", ""))[0]
        ordem = re.search(r'CALL|PUT', texto.upper())[0].lower()
        timeframe = re.search(
            r'[MH][1-6]?[0-5]', texto.upper())
        if timeframe: 
            if "M" in timeframe[0].upper(): 
                timeframe = int(timeframe[0].strip("M"))
            else: 
                timeframe = int(timeframe[0].strip("H")) * 60
        else: timeframe = 0
    except Exception as e:
        print(type(e), e)
        print(f"Revise o comando {texto}")
        return {}

    comando = {
        "data": data,
        "hora": hora,
        "par": par,
        "ordem": ordem,
        "timeframe": timeframe
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
    def __init__(self, token, channel, permitidos, mensagem):
        print(mensagem)
        self.token = token
        self.bot = amanobot.Bot(token)
        self.my_id = self.bot.getMe()['id']
        self.listas_de_entradas = {}
        self.channel, self.permitidos = channel, permitidos
        self.cadeado = threading.Lock()
        
        self.IQ = IQ_Option("hiyivo1180@tmail7.com", "senha123")
        self.IQ.connect()

        self.rodando = True
        self.escolher_lista = False
        self.esperar_lista = False
        self.parar_transmissao = False
        self.esperar_grupo = False
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
                    canal, __import__("templates").inicio)
            except (BotWasBlockedError, BotWasKickedError):
                self.channel.remove(canal)
                continue
            except Exception as e:
                if "chat not found" in e.description:
                    self.channel.remove(canal)
                    continue
                else:
                    print(e)
                    self.bot = amanobot.Bot(self.token)
                    mensagem = self.bot.sendMessage(
                        canal, __import__("templates").inicio)
            
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
                            i += 1
                        except (BotWasBlockedError, 
                                BotWasKickedError):
                            self.channel.remove(self.channel[i])
                        except Exception as e:
                            if "rights" in str(e):
                                self.bot.sendMessage(chat_id, 
                                "Preciso ter permissões para enviar mensagem, me coloque como admnistrador.")
                            else:
                                print(e)
                                self.bot = amanobot.Bot(self.token)
                                time.sleep(1)
                    if (len(self.channel) > 0 and
                    time.time() - hora_parcial > (3600 * 3)):
                        hora_parcial = time.time()
                        self.mandar_parcial(atual)
                        self.mandar_completa(atual)
            
        self.mandar_parcial(atual)

        if not self.listas_de_entradas[atual]['on']:
            del self.listas_de_entradas[atual]

        self.bot.sendMessage(chat_id, "Transmissão finalizada")
        print("Terminou a transmissão")

    def editar_mensagem(self, message_id, resposta):
        try:
            self.bot.editMessageText(message_id, resposta)
        except Exception as e:
            if "modified" not in str(e):
                self.bot = amanobot.Bot(self.token)
                self.bot.editMessageText(message_id, resposta)

    def mandar_completa(self, atual):
        win = self.listas_de_entradas[atual]["win"]
        loss = self.listas_de_entradas[atual]["loss"]
        timeframe = self.listas_de_entradas[atual]['timeframe']
        gales = self.listas_de_entradas[atual]['gales']
        result = self.listas_de_entradas[atual]['result']
        assertividade = round(
            win / (win + loss) * 100 if 
            win + loss > 0 else 100, 2)
        resposta = __import__("templates").completo.format(
            timeframe = timeframe, gales = gales,
            result = result, quality = assertividade
        )
        for canal in self.channel:
            message_id = self.listas_de_entradas[atual]['id'][canal]
            self.editar_mensagem(message_id, resposta)

    def mandar_parcial(self, atual):
        win = self.listas_de_entradas[atual]["win"]
        loss = self.listas_de_entradas[atual]["loss"]
        winsg = self.listas_de_entradas[atual]["winsg"]
        gales = self.listas_de_entradas[atual]["gales"]
        timeframe = self.listas_de_entradas[atual]["timeframe"]
        fechados = self.listas_de_entradas[atual]["closed"]
        if win > 0 or loss > 0:
            mensagem_parcial = __import__("templates").parcial.format(
                gales = gales, timeframe = timeframe, win = win, 
                fechados = fechados, loss = loss, winsg = winsg,
                wincg = win - winsg, quality = round(
                    win / (win + loss) * 100, 2))
            for canal in self.channel:
                try:
                    self.bot.sendMessage(canal, mensagem_parcial)
                except:
                    self.bot = amanobot.Bot(self.token)
                    self.bot.sendMessage(canal, mensagem_parcial)

    def enviar_relatorio(self, paridade, timeframe, hora_entrada, 
        ordem, direcao, texto_gales, message_id):
        tendencia, rsi, taxa = self.calcular_tendencia(
                paridade, timeframe)
        suporte_resistencia = self.devolve_suporte_resistencia(
            paridade, timeframe, taxa)
        self.editar_mensagem(message_id, 
            __import__("templates").operacao.format(
            paridade = paridade, timeframe = timeframe // 60, 
            hora_entrada = hora_entrada, ordem = ordem, 
            direcao = direcao.upper(), gales = texto_gales,
            taxa = taxa, tendencia = tendencia, rsi = rsi,
            suporte_resistencia = suporte_resistencia))

    def verificar_aberto(self, paridade, timeframe):
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
        return esta_aberto

    def mandar_resultado(
        self, message_id, paridade, hora_entrada, timeframe, 
        direcao, max_gales, atual, apagar, texto_gales = ""):
        time.sleep(240)
        ordem = '⬆' if direcao.lower() == "call" else '⬇'
        gales, win, timeframe = 0, False, timeframe * 60
        if len(max_gales) == 1:
            texto_gales = f"🐔 Até {max_gales[0]} gales" 

        esta_aberto = self.verificar_aberto(paridade, timeframe)
        espera = datetime.now().timestamp() + (timeframe * 3) + 65

        if esta_aberto:
            self.enviar_relatorio(paridade, timeframe, hora_entrada, 
                ordem, direcao, texto_gales, message_id)

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
        resultado = '🔒' if not esta_aberto else (
            gales * '🐔') + '✅' if win else '❌'

        resposta = __import__("templates").resultado.format(
            paridade = paridade, timeframe = timeframe // 60, 
            hora_entrada = hora_entrada, ordem = ordem, 
            direcao = direcao.upper(), gales = texto_gales,
            resultado = resultado
        )
        
        with self.cadeado:
            result_text = f"{hora_entrada} {paridade} {direcao.upper()} {resultado}"
            if atual in self.listas_de_entradas: 
                entrada = self.listas_de_entradas[atual]
                if result_text not in entrada['result'].split("\n"):
                    try:
                        # Salva informações caso alguém ainda não salvou
                        entrada['result'] += f"{result_text}\n"
                        if win:
                            entrada['win'] += 1
                            if gales == 0:
                                entrada["winsg"] += 1
                        elif esta_aberto:
                            entrada["loss"] += 1
                        else:
                            entrada["closed"] += 1

                        print(f"Salvando {hora_entrada} {paridade}: {message_id}")
                        self.mandar_completa(atual)
                    except Exception as e:
                        print(type(e), e)

        self.editar_mensagem(message_id, resposta)

        if apagar:
            self.mandar_parcial(atual)
            del self.listas_de_entradas[atual]

    def calcular_tendencia(
        self, par, timeframe):
        '''
        Devolve se a entrada está de acordo com SMA
        '''
        import numpy

        periodo = 21
        dados = [
            x['close'] for x in self.IQ.get_candles(
            par, timeframe, periodo * 2, time.time())
        ]
        # Calcula a SMA
        pesos = numpy.repeat(1.0, periodo) / periodo
        smas = numpy.convolve(
            dados, pesos, 'valid').tolist()
        diferenca = smas[-1] - smas[-periodo]
        tendencia =  '⬆' if diferenca > 0 else '⬇'
        rsi = round(self.calcular_rsi(dados, 14), 2)    

        return tendencia, rsi, dados[-1]

    def calcular_rsi(self, values, period):
        '''
        Found in a friend code
        '''
        import numpy

        deltas = numpy.diff(values)
        seed = deltas[:period + 1]
        up = seed[(seed >= 0)].sum() / period
        down = -seed[(seed < 0)].sum() / period
        rs = up / down
        rsi = numpy.zeros_like(values)
        rsi[:period] = 100.0 - 100.0 / (1.0 + rs)
        for i in range(period, len(values)):
            delta = deltas[(i - 1)]
            if delta > 0:
                upval = delta
                downval = 0.0
            else:
                upval = 0.0
                downval = -delta
            up = (up * (period - 1) + upval) / period
            down = (down * (period - 1) + downval) / period
            rs = up / down
            rsi[i] = 100.0 - 100.0 / (1.0 + rs)

        return rsi[-1:][0]

    def devolve_suporte_resistencia(self, paridade, timeframe, vela):
        '''
        Calcula o suporte ou resistência mais próxmio
        '''
        velas = self.IQ.get_candles(
            paridade, timeframe, 1000, time.time())

        dados = []
        for i in velas:
            dados.extend([i['close'], i['max'], i['min']])

        maximos_minimos = []
        em_processo = []
        suportes_resistencias = []

        def proximo(a, b, rate = 0.00005):
            if a - rate < b < a + rate:
                return True
            return False

        def procura_perto(tipo, item):
            for i in maximos_minimos:
                if proximo(i, item):
                    if item in maximos_minimos:
                        maximos_minimos.remove(item)
                        if item not in em_processo:
                            em_processo.append(item)
                    else:
                        verifica = True
                        excluir = None
                        for supres in suportes_resistencias:
                            if proximo(item, supres):
                                verifica = False
                                break
                            elif proximo(item, supres, 0.0001):
                                excluir = supres

                        if verifica:
                            if excluir != None:
                                if tipo == "max":
                                    item = item if item > excluir else excluir
                                else:
                                    item = item if item < excluir else excluir
                            if item not in suportes_resistencias:
                                suportes_resistencias.append(item)

        periodo = 20

        for i in range(0, len(dados), periodo):
            analise = dados[i:i + periodo]
            maximo = max(analise)
            if maximo not in maximos_minimos:
                maximos_minimos.append(maximo)
            else: procura_perto("max", maximo)
            
            minimo = min(analise)
            if minimo not in maximos_minimos:
                maximos_minimos.append(minimo)
            else: procura_perto("min", minimo)

        if len(suportes_resistencias) > 0:
            mais_proximo = suportes_resistencias[0]
            for i in suportes_resistencias:
                if abs(vela - i) < mais_proximo:
                    mais_proximo = i
            return mais_proximo
        else:
            return "-"

    def formatar_entradas(self, tipo, periodo, comandos):
        '''
        Recebe uma lista de comandos, e formata do jeito correto.
            tipo: quantidade de gales no formato "🐔 Até 1 gale"
            periodo: timeframe no formato "M1"
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
                paridade = comando['par']
                direcao = comando['ordem']
                key = str(indice)+"/"+str(dia)+"/"+hora
                resultado[key] = {}
                resultado[key]['msg'] = __import__("templates").entradas.format(
                    hora = hora, periodo = periodo,
                    gales = tipo, paridade = paridade, 
                    emoji_dir = "⬆" if direcao.lower() == "call" else "⬇", direcao = direcao.upper()
                )
                resultado[key]['par'] = paridade
                resultado[key]['hora'] = hora
                resultado[key]['gale'] = [
                    int(x) for x in tipo.split() if x.isdigit()]
                resultado[key]['direcao'] = direcao.lower()
                resultado[key]['periodo'] = int(periodo.strip("M"))
                resultado[key]['result'] = "?"
            except Exception as e:
                print(type(e), e)
                print("Não entendi a entrada:", comando)
        return resultado

    def mostrar_comandos(self, comando):
        '''
        Função que mostra os botões do menu
        Chamada quando fala /comandos
        '''
        user = comando["from"]
        try:
            nome = user["first_name"] + " " + user["last_name"]
        except:
            nome = ""

        keyboard = InlineKeyboardMarkup(inline_keyboard = [
            [InlineKeyboardButton(
                text = "Registrar nova lista", 
                callback_data = "newlist"
            ), 
            InlineKeyboardButton(
                text = "Ver listas registradas", 
                callback_data = "showlist"
            )],
            [InlineKeyboardButton(
                text = "Começar transmissão", 
                callback_data = "start"
            ),
            InlineKeyboardButton(
                text = "Parar transmissão",
                callback_data = "stop"
            )],
            [InlineKeyboardButton(
                text = "Adicionar novo grupo", 
                callback_data = "newgroup"
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

        self.esperar_lista = False
        self.esperar_grupo = False
        self.escolher_lista = False
        self.parar_transmissao = False

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
        elif query_data == "newgroup":
            print("Entrando no modo de novo grupo")
            self.bot.answerCallbackQuery(
                query_id, text = "Modo adicionar grupo")
            self.bot.sendMessage(
                from_id, "Adicione o bot no grupo.")
            self.esperar_grupo = True
        elif query_data == "showlist":
            print("Entrando no modo de mostragem")
            self.bot.answerCallbackQuery(
                query_id, text = "Modo mostrar lista")

            for options in self.listas_de_entradas.values():
                if not options['deleted']:
                    resposta = ""
                    for entrada in options['lista'].values():
                        resposta += entrada['msg']
                    if resposta == "":
                        resposta = "Nenhuma lista registrada."
                    self.bot.sendMessage(from_id, resposta)
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

    def recebe_comandos(self, comando):
        '''
        Função que é chamada caso falar no chat
        '''
        def pegar_gales(lista):
            for entrada in lista:
                if "1 gal" in entrada.lower():
                    return "🐔 Até 1 gale"
                elif "2 gal" in entrada.lower():
                    return "🐔 Até 2 gales"
            return ""

        def pegar_periodo(lista):
            for entrada in lista:
                if "M15" in entrada.upper():
                    return "M15"
                elif "M5" in entrada.upper():
                    return "M5"
                elif "M1" in entrada.upper():
                    return "M1"
                elif "M30" in entrada.upper():
                    return "M30"
            return "M5"

        if comando != []:
            content_type, chat_type, chat_id = amanobot.glance(comando)

            if chat_id in self.permitidos:
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
                    tipo = pegar_gales(entradas)
                    periodo = pegar_periodo(entradas)
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
                        self.listas_de_entradas[int(key)]['deleted'] = False
                        self.bot.sendMessage(
                            chat_id, "Transmissão cancelada", 
                            reply_markup = ReplyKeyboardRemove())
                    except:
                        self.bot.sendMessage(chat_id, 
                            "Não consegui parar a transmissão", 
                            reply_markup = ReplyKeyboardRemove())
                    self.parar_transmissao = False
                else:
                    self.mostrar_comandos(comando)
            elif comando['chat'].get("type") in [
                "group", "supergroup", "channel"]:
                adicionar = comando.get('new_chat_participant')
                remover = comando.get('left_chat_participant')
                if adicionar:
                    adicionar = adicionar.get('id') == self.my_id
                elif remover:
                    remover = remover.get('id') == self.my_id
                if (self.esperar_grupo and adicionar and 
                    comando['chat']['id'] not in self.channel):
                    self.esperar_grupo = False
                    self.channel.append(comando['chat']['id'])
                elif remover and comando['chat']['id'] in self.channel:
                    self.channel.remove(comando['chat']['id'])
                pprint.pprint(self.channel)
            else:
                pprint.pprint(comando)

if __name__ == "__main__":
    verificador = True
    try:
        with open("settings.json", "r+") as file:
            info = json.load(file)
        program = Telegram(info["token"], info["canal"], info["id"], "Iniciando bot...")
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
