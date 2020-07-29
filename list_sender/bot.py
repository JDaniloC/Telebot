try:
    import amanobot
except ModuleNotFoundError:
    from subprocess import call
    call(["pip", "install", "amanobot"])
    import amanobot

import time, pprint, traceback, json, re, threading
from datetime import datetime
from amanobot.loop import MessageLoop
from amanobot.namedtuple import (
    InlineKeyboardMarkup, InlineKeyboardButton)

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
            hoje = datetime.now()
            data = [hoje.day, hoje.month, hoje.year]
        hora = re.search(r'\d{2}:\d{2}', texto)[0]
        hora = [int(x) for x in re.split(r'\W', hora)]
        par = re.search(r'[A-Za-z]{6}', texto.replace("/", ""))[0]
        ordem = re.search(r'CALL|PUT|call|put', texto)[0].lower()
    except Exception as e:
        print(type(e), e)
        print(f"Ocorreu um erro no arquivo de entradas, revise o comando {texto}")
        data = [1, 1, 2000]
        hora = [00, 00]
        par = "EURUSD"
        ordem = "PUT"

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
        self.bot = amanobot.Bot(token)
        self.lista_entradas = {}
        self.esperar_lista = False
        self.channel = channel
        self.meu_id = meu_id
        
        self.rodando = True
        self.transmitindo = True

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
        alvo = data.replace(day = int(dia), hour = horas, minute = minutos, second = 0, microsecond = 0)
        alvo = datetime.fromtimestamp(alvo.timestamp() - 300)
        segundos = alvo.timestamp() - datetime.now().timestamp()
        if segundos > 0:
            print(f"Esperando até as {alvo}")
            self.bot.sendMessage(identificador, f"\n [...] Próxima entrada será às {alvo} [...]")
            time.sleep(segundos)
            return True
        elif segundos > -5:
            return True
        return False

    def transmissao(self, chat_id):
        '''
        Função que percorre a lista de entradas e envia para o canal
        '''
        print("Começando a transmitir")
        for key in self.lista_entradas:
            if self.transmitindo and self.esperarAte(chat_id, key):
                if self.transmitindo:
                    for canal in self.channel:
                        try:
                            self.bot.sendMessage(canal, self.   lista_entradas[key])
                        except Exception as e:
                            self.bot.sendMessage(chat_id, f"Eu tive um  erro: {e}. Continuando...")
        self.bot.sendMessage(chat_id, "Transmissão finalizada")
        print("Terminou a transmissão")

    def formatar_entradas(self, comandos):
        '''
        Recebe uma lista de comandos, e formata do jeito correto.
        '''
        resultado = {}
        for indice, comando in enumerate(comandos):
            try:
                comando = pegar_comando(comando)
                dia, mes, ano = comando['data']
                data = "/".join(
                    list(map(strDateHour, comando["data"])))
                hora = ":".join(
                    list(map(strDateHour, comando["hora"])))
                par = comando['par']
                direcao = comando['ordem']
                resultado[str(indice)+"/"+str(dia)+"/"+hora] = f'''
🏹 M.M_007 Bot 🏹
⏱ ENTRADA {hora}
💲 Período: M5  
⚠️ Ativo: {par} 
{"⬆" if direcao.lower() == "call" else "⬇"} Direção: {direcao.upper()}
                '''
            except Exception as e:
                print(type(e), e)
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
                from_id, "Me envie a próxima lista:"
            )
            self.esperar_lista = True
        elif query_data == "showlist":
            print("Entrando no modo de mostragem")
            self.bot.answerCallbackQuery(
                query_id, text = "Modo mostrar lista")
            if self.lista_entradas == {}:
                mesagem = "Nenhuma lista registrada"
            else:
                mesagem = "Lista atual:"
            self.bot.sendMessage(
                from_id, mesagem
            )
            
            for key in self.lista_entradas:
                self.bot.sendMessage(
                    from_id, self.lista_entradas[key] + "\n")
        elif query_data == "start":
            print("Entranho no modo de transmissão")
            self.bot.answerCallbackQuery(
                query_id, text = "Modo enviar lista")
            self.transmitindo = True
            threading.Thread(
                target = self.transmissao, args = (from_id,)
            ).start()
        elif query_data == "stop":
            self.transmitindo = False
            self.bot.answerCallbackQuery(
                query_id, "Transmissão parada.")
        elif query_data == "desligar":
            self.bot.answerCallbackQuery(
                query_id, "Bot desligado.")
            self.rodando = False

    def recebe_comandos(self, comando):
        '''
        Função que é chamada caso falar no chat
        '''

        if comando != []:
            content_type, chat_type, chat_id = amanobot.glance(comando)

            if chat_id in self.meu_id:
                if self.esperar_lista:
                    pprint.pprint(comando)
                    self.lista_entradas = self.formatar_entradas(comando.get('text').split("\n"))
                    self.esperar_lista = False
                    self.bot.sendMessage(chat_id, "Lista salva")
                elif comando.get('text') in [
                    "/comandos", 
                    "/start"]:
                    self.mostrar_comandos(comando)
            elif comando['chat'].get("type") in ["group", "supergroup", "channel"]:
                if comando['chat']['id'] not in self.channel:
                    self.channel.append(comando['chat']['id'])
            else:
                pprint.pprint(comando)

if __name__ == "__main__":
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