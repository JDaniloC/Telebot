import json, bot, time, requests
from datetime import timedelta
from tkinter import messagebox
from tkinter import *

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
            params = { "email": email, "botName": "listsender"
        }).json()
        if email in response:
            tempo_restante = response[email]["timestamp"] - time.time()
            validacao, mensagem = devolve_restante(tempo_restante)
        else:
            validacao, mensagem = False, "Compre uma licença!"
    except:
        validacao, mensagem = False, "Servidor em manutenção!"
    return validacao, mensagem

class Config(Frame):
    def __init__(self, janela):
        super().__init__(janela)
        self.janela = janela
        self.pack(fill = X, padx = 10, pady = 10)
        self.widgets()

    def widgets(self):
        titulos = ["Email", "Token", "Canal", "Id"]
        self.entradas = {}
        for i in range(len(titulos)):
            Label(self, text = titulos[i]).grid(row = i)
            self.entradas[titulos[i].lower()] = Entry(self, width = 50)
            self.entradas[titulos[i].lower()].grid(row = i, column = 1)
        self.texto = Label(self, justify = LEFT, text = """
    Infos:
        Token: Conseguir com o Botfather do telegram
        Canais: O link/id dos grupos/canais separado por vírgula
        Id: Os contatos que podem falar com o bot"""
            )
        self.texto.grid(row = len(titulos), columnspan = 2)

        Button(self, text = "Salvar", command = self.salvar
            ).grid(row = 5, columnspan = 2)
        Button(self, text = "Iniciar", command = self.iniciar
            ).grid(row = 5, sticky = E, padx = 20, columnspan = 2)
        self.carregar()

    def carregar(self):
        try:
            with open("settings.json", "r+") as file:
                info = json.load(file)
            info['canal'] = ", ".join(map(str, info['canal']))
            info["id"] = ", ".join(list(map(str, info["id"])))
            for key in self.entradas:
                self.entradas[key].insert(END, info[key])
        except Exception as e:
            print(e)

    def tratar_dados(self, info):
        if info['canal'] != "": 
            info['canal'] = info['canal'].strip().replace(" ", '').split(",")
        else: info['canal'] = []

        if info['id'] != "": info['id'] = list(map(int, 
            info['id'].strip().replace(" ", "").split(",")))
        else: info['id'] = []
        return info

    def salvar(self):
        info = {
            key: value.get() for key, value in self.entradas.items()
        }
        info = self.tratar_dados(info)

        with open("settings.json", "w") as file:
            json.dump(info, file, indent= 2)

        messagebox.showinfo("Status", "Configuração salva")

    def iniciar(self):
        self.salvar()
        info = {
            key: value.get() for key, value in self.entradas.items()
        }
        info = self.tratar_dados(info)

        validacao, mensagem = autenticar_licenca(info["email"])
        if validacao:
            self.janela.destroy()
            bot.Telegram(info["token"], info["canal"], info["id"], mensagem)
        else:
            self.texto["text"] = mensagem

if __name__ == "__main__":
    janela = Tk()
    janela.title("Config")
    Config(janela).mainloop()