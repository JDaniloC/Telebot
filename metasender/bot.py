import time, pprint, traceback, json, threading 
from iqoptionapi.stable_api import IQ_Option
import re, amanobot, templates, csv
from datetime import datetime
from pathlib import Path

from amanobot.loop import MessageLoop
from amanobot.exception import (
    BotWasBlockedError, BotWasKickedError)
from amanobot.namedtuple import (
    InlineKeyboardMarkup, InlineKeyboardButton)

def escreve_erros(erro):
    '''
    Guarda o traceback do erro em um arquivo.log
    '''
    linhas = " -> ".join(re.findall(r'line \d+', 
        str(traceback.extract_tb(erro.__traceback__))))
    with open("errors.log", "a") as file:
        file.write(f"{type(erro)} - {erro}:\n{linhas}\n")

class Telegram:
    def __init__(self, token, channel, meu_id, meta_path):
        self.meta_path = Path(meta_path)
        self.token = token
        self.bot = amanobot.Bot(token)
        self.my_id = self.bot.getMe()['id']
        self.listas_de_entradas = {}
        self.channel = channel
        self.id_permitidos = meu_id
        self.cadeado = threading.Lock()
        
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

    def procurar_sinais(self):
        hoje = datetime.fromtimestamp(
            datetime.utcnow().timestamp() - 10800)
            
        caminho = self.meta_path / "Files" / f'{hoje.strftime("%Y%m%d")}_retorno.csv'
        resultado = []
        try:
            with open(caminho) as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=',')
                csv_reader.__next__()
                
                delay = round(time.time()) - 1
            
                for linha in csv_reader:
                    if delay <= int(linha[0]):
                        print("SINAL: ", 
                            datetime.fromtimestamp(int(linha[0])))
                        resultado.append(linha)
        except Exception as e:
            print(type(e), e)
            resultado = []
        finally:
            return resultado

    def esperarAte(self, identificador, timestamp):
        '''
        Espera até determinada data/hora:minuto
        Recebe um dia/hora:minuto
        '''        
        alvo = datetime.fromtimestamp(timestamp)
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

    def transmissao(self, chat_id):
        '''
        Função que percorre a lista de entradas e envia para o canal
        '''
        print("Começando a transmitir")
        self.listas_de_entradas = {}
        for canal in self.channel:    
            try:
                mensagem = self.bot.sendMessage(
                    canal, templates.inicio)
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
                        canal, templates.inicio)
            
            self.listas_de_entradas[canal] = (canal, mensagem['message_id'])
        
        # Resultados
        self.listas_de_entradas['on'] = True
        self.listas_de_entradas["win"] = 0
        self.listas_de_entradas["loss"] = 0
        self.listas_de_entradas["winsg"] = 0
        self.listas_de_entradas["closed"] = 0
        self.listas_de_entradas['result'] = ""
        hora_parcial = time.time()

        lista_entradas = []
        while self.listas_de_entradas['on']:
            lista_entradas = set(self.procurar_sinais()) # Pegar os elementos únicos
            for entrada in lista_entradas:
                entrada = self.formatar_entrada(entrada)
                if self.esperarAte(chat_id, entrada['timestamp']):
                    i = 0
                    while i < len(self.channel):
                        try:
                            mensagem = self.bot.sendMessage(
                                self.channel[i],  entrada['msg'])
                            par = entrada['par']
                            hora = entrada['hora']
                            direcao = entrada['direcao']
                            timeframe = entrada['periodo']
                            gales = entrada['gales']
                            threading.Thread(
                                target=self.mandar_resultado,
                                args = ((self.channel[i], 
                                    mensagem['message_id']), 
                                    par, hora, timeframe, 
                                    direcao, gales)).start()
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
                        self.mandar_parcial()
                        self.mandar_completa()
            time.sleep(0.5)
            
        self.mandar_parcial()

        self.bot.sendMessage(chat_id, "Transmissão finalizada")
        print("Terminou a transmissão")

    def editar_mensagem(self, message_id, resposta):
        try:
            self.bot.editMessageText(message_id, resposta)
        except Exception as e:
            if "modified" not in str(e):
                self.bot = amanobot.Bot(self.token)
                self.bot.editMessageText(message_id, resposta)

    def mandar_completa(self):
        win = self.listas_de_entradas["win"]
        loss = self.listas_de_entradas["loss"]
        result = self.listas_de_entradas['result']
        assertividade = round(
            win / (win + loss) * 100 if 
            win + loss > 0 else 100, 2)
        resposta = templates.completo.format(
            result = result, quality = assertividade)
        for canal in self.channel:
            message_id = self.listas_de_entradas[canal]
            self.editar_mensagem(message_id, resposta)

    def mandar_parcial(self):
        win = self.listas_de_entradas["win"]
        loss = self.listas_de_entradas["loss"]
        winsg = self.listas_de_entradas["winsg"]
        fechados = self.listas_de_entradas["closed"]
        if win > 0 or loss > 0:
            mensagem_parcial = templates.parcial.format(
                win = win, fechados = fechados, loss = loss, 
                winsg = winsg, wincg = win - winsg,
                quality = round(win / (win + loss) * 100, 2))
            for canal in self.channel:
                try:
                    self.bot.sendMessage(canal, mensagem_parcial)
                except:
                    self.bot = amanobot.Bot(self.token)
                    self.bot.sendMessage(canal, mensagem_parcial)

    def mandar_resultado(self, message_id, paridade, hora_entrada, 
        timeframe, direcao, max_gales):
        
        timeframe *= 60
        espera = datetime.now().timestamp() + (timeframe * 3) + 10

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
        texto_gales = f"🐔 Até {max_gales} gales"
        ordem = '⬆' if direcao.lower() == "call" else '⬇'
        tempo = timeframe // 60
        if tempo >= 60:
            tempo = f"H{tempo//60}"
        else:
            tempo = f"M{tempo}"

        if esta_aberto:
            tendencia, rsi, taxa = self.calcular_tendencia(
                paridade, timeframe)
            suporte_resistencia = self.devolve_suporte_resistencia(
                paridade, timeframe, taxa)
            self.editar_mensagem(message_id, templates.operacao.format(
                paridade = paridade, timeframe = timeframe // 60, 
                hora_entrada = hora_entrada, ordem = ordem, 
                direcao = direcao.upper(), gales = texto_gales,
                taxa = taxa, tendencia = tendencia, rsi = rsi,
                suporte_resistencia = suporte_resistencia
            ))

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

        if gales == 2 and max_gales == 1:
            win = False

        resultado = '🔒' if not esta_aberto else (gales * '🐔') + '✅' if win else '❌'

        resposta = templates.resultado.format(
            paridade = paridade, timeframe = timeframe // 60, 
            hora_entrada = hora_entrada, ordem = ordem, 
            direcao = direcao.upper(), gales = texto_gales,
            resultado = resultado
        )
        
        with self.cadeado:
            entrada = f"{hora_entrada} M{timeframe // 60} {paridade} {direcao.upper()} {resultado}"
            if entrada not in self.listas_de_entradas['result'].split("\n"):
                try:
                    # Salva informações caso alguém ainda não salvou
                    self.listas_de_entradas['result'] += f"{entrada}\n"
                    if win:
                        self.listas_de_entradas['win'] += 1
                        if gales == 0:
                            self.listas_de_entradas["winsg"] += 1
                    elif esta_aberto:
                        self.listas_de_entradas["loss"] += 1
                    else:
                        self.listas_de_entradas["closed"] += 1

                    print(f"Salvando {hora_entrada} {paridade}: {message_id}")
                    self.mandar_completa()
                except Exception as e:
                    print(type(e), e)

        self.editar_mensagem(message_id, resposta)

    def calcular_tendencia(self, par, timeframe):
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

    def formatar_entrada(self, comando):
        '''
        Recebe uma lista de comandos, e formata do jeito correto.
            tipo: quantidade de gales no formato "🐔 Até 1 gale"
            comando: (timestamp, paridade, direcao, periodo)
        '''
        resultado = {}
        try:
            timestamp = int(comando[0])
            hora = datetime.fromtimestamp(
                timestamp).strftime("%H:%M")
            paridade = comando[1].upper()
            direcao = comando[2].upper()
            periodo = "M" + comando[3]

            resultado = {}
            resultado['timestamp'] = timestamp
            resultado['msg'] = templates.entradas.format(
                hora = hora, periodo = periodo,
                gales = "🐔 Até 2 gales", paridade = paridade, 
                emoji_dir = "⬆" if direcao.lower() == "call" else "⬇", 
                direcao = direcao.upper())
            resultado['par'] = paridade
            resultado['hora'] = hora
            resultado['gales'] = 2
            resultado['direcao'] = direcao.lower()
            resultado['periodo'] = int(periodo.strip("M"))
            resultado['result'] = "?"
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
        nome = user["first_name"] + " " + user["last_name"]

        keyboard = InlineKeyboardMarkup(inline_keyboard = [
            [InlineKeyboardButton(
                text = "Começar transmissão", 
                callback_data = "start"
            )],
            [InlineKeyboardButton(
                text = "Adicionar novo grupo", 
                callback_data = "newgroup"
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

        self.bot.sendMessage(comando["chat"]["id"], 
            f"Olá {nome}, o que você deseja?",
            reply_markup = keyboard
        )

    def resposta_botao(self, comando):
        '''
        Função que recebe os comandos dos botões
        '''

        query_id, from_id, query_data = amanobot.glance(
            comando, flavor = "callback_query")

        self.esperar_grupo = False
        self.parar_transmissao = False

        if query_data == "newgroup":
            print("Entrando no modo de recebimento")
            self.bot.answerCallbackQuery(
                query_id, text = "Modo adicionar grupo")
            self.bot.sendMessage(
                from_id, "Adicione o bot no grupo.")
            self.esperar_grupo = True

        elif query_data == "start":
            print("Entranho no modo de transmissão")
            self.bot.answerCallbackQuery(
                query_id, text = "Modo enviar sinais")
            threading.Thread(
                target = self.transmissao, 
                args = (from_id, ), daemon = True
            ).start()
            self.bot.sendMessage(from_id, "Transmissão iniciada")
            
        elif query_data == "stop":
            self.listas_de_entradas['on'] = False

        elif query_data == "desligar":
            self.bot.answerCallbackQuery(query_id, "Bot desligado.")
            self.bot.sendMessage(from_id, "Bot desligado")
            self.rodando = False

    def recebe_comandos(self, comando):
        '''
        Função que é chamada caso falar no chat
        '''

        if comando != []:
            _, __, chat_id = amanobot.glance(comando)

            if chat_id in self.id_permitidos:
                self.mostrar_comandos(comando)
            elif self.esperar_grupo and comando['chat'].get(
                "type") in ["group", "supergroup", "channel"]:
                adicionar = comando.get('new_chat_participant')
                remover = comando.get('left_chat_participant')
                if adicionar:
                    adicionar = adicionar.get('id') == self.my_id
                elif remover:
                    remover = remover.get('id') == self.my_id
                
                identificador = comando['chat']['id']
                if adicionar and identificador not in self.channel:
                    self.esperar_grupo = False
                    self.channel.append(identificador)
                elif remover and identificador in self.channel:
                    self.channel.remove(identificador)
                pprint.pprint(self.channel)
            else:
                pprint.pprint(comando)

if __name__ == "__main__":
    verificador = True
    try:
        with open("settings.json", "r+") as file:
            info = json.load(file)
        program = Telegram(
            info["token"], info["canais"], 
            info["id"], info["metatrader"])
        verificador = program.rodando
        with open("settings.json", "w") as file:
            info['canais'] = program.channel
            json.dump(info, file, indent = 2)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print("Aconteceu um problema, se persistir chame o técnico")
        escreve_erros(e)
    if verificador:
        input("Digite Enter para fechar")
