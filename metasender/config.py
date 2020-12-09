import json, bot
from tkinter import *
from os import listdir
from tkinter import messagebox
from datetime import timedelta, datetime
from cryptography.fernet import Fernet

class Config(Frame):
    def __init__(self, janela):
        super().__init__(janela)
        self.janela = janela
        self.pack(fill = X, padx = 10, pady = 10)
        self.widgets()

    def widgets(self):
        titulos = ["Token", "Metatrader", "Canais", "Id"]
        self.entradas = {}
        for i in range(len(titulos)):
            Label(self, text = titulos[i]).grid(row = i)
            self.entradas[titulos[i].lower()] = Entry(self, width = 50)
            self.entradas[titulos[i].lower()].grid(row = i, column = 1)
        Label(self, justify = LEFT, text = """
    Infos:
        Token: Conseguir com o Botfather do telegram
        Metatrader: Caminho até a pasta MQL4
        Canais: O link/id dos grupos/canais separado por vírgula
        Id: Os contatos que podem falar com o bot"""
            ).grid(row = len(titulos), columnspan = 2)

        Button(self, text = "Salvar", command = self.salvar
            ).grid(row = 5, columnspan = 2)
        Button(self, text = "Iniciar", command = self.iniciar
            ).grid(row = 5, sticky = E, padx = 20, columnspan = 2)
        self.carregar()

    def carregar(self):
        try:
            with open("settings.json", "r+") as file:
                info = json.load(file)
            info['canais'] = ", ".join(map(str, info['canais']))
            info["id"] = ", ".join(list(map(str, info["id"])))
            for key in self.entradas:
                self.entradas[key].insert(END, info[key])
        except Exception as e:
            print(e)

    def tratar_dados(self, info):
        if info['canais'] != "": info['canais'] = info['canais'].strip().replace(" ", '').split(",")
        else: info['canais'] = []

        if info['id'] != "": info['id'] = list(map(int, info['id'].strip().replace(" ", "").split(",")))
        else: info['id'] = []
        return info

    def salvar(self):
        info = {
            key: value.get() for key, value in self.entradas.items()
        }
        info = self.tratar_dados(info)
        info["metatrader"] = info["metatrader"].replace("\\", "/")
        
        with open("settings.json", "w") as file:
            json.dump(info, file, indent= 2)

        messagebox.showinfo("Status", "Configuração salva")

    def iniciar(self):
        self.salvar()
        info = {
            key: value.get() for key, value in self.entradas.items()
        }
        info = self.tratar_dados(info)
        info["metatrader"] = info["metatrader"].replace("\\", "/")

        self.janela.destroy()
        bot.Telegram(
            info["token"], info["canais"], info["id"], info["metatrader"])

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
        dia, mes, ano, hora, minuto = 9, 11, 2020, 0, 0
    
    data_final = datetime(ano, mes, dia, hora, minuto)
    tempo_restante = datetime.timestamp(data_final) - datetime.timestamp(datetime.now())

    return tempo_restante

if __name__ == "__main__":
    restante = devolve_licenca()
    if restante > 0:
        horas_minutos = timedelta(seconds = restante)
        print(str(horas_minutos)[:-7].replace('days', 'dias'))
        janela = Tk()
        janela.title("Config")
        Config(janela).mainloop()
    else:
        input("O período teste acabou.")