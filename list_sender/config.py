import json, bot
from tkinter import *
from tkinter import messagebox

class Config(Frame):
    def __init__(self, janela):
        super().__init__(janela)
        self.janela = janela
        self.pack(fill = X, padx = 10, pady = 10)
        self.widgets()

    def widgets(self):
        titulos = ["Token", "Canal", "Id"]
        self.entradas = {}
        for i in range(len(titulos)):
            Label(self, text = titulos[i]).grid(row = i)
            self.entradas[titulos[i].lower()] = Entry(self, width = 40)
            self.entradas[titulos[i].lower()].grid(row = i, column = 1)
        
        Button(self, text = "Salvar", command = self.salvar).grid(row = 4)
        Button(self, text = "Iniciar", command = self.iniciar).grid(row = 4, column = 1)
        self.carregar()

    def carregar(self):
        with open("settings.json", "r+") as file:
            info = json.load(file)

        info['canal'] = ", ".join(map(str, info['canal']))
        info["id"] = ", ".join(list(map(str, info["id"])))
        for key in self.entradas:
            self.entradas[key].insert(END, info[key])

    def salvar(self):
        info = {
            key: value.get() for key, value in self.entradas.items()
        }
        info['canal'] = info['canal'].strip().replace(" ", '').split(",")
        info["id"] = list(map(int, info["id"].strip().replace(" ", "").split(",")))
        with open("settings.json", "w") as file:
            json.dump(info, file, indent= 2)

        messagebox.showinfo("Status", "Configuração salva")

    def iniciar(self):
        info = {
            key: value.get() for key, value in self.entradas.items()
        }
        info['canal'] = info['canal'].strip().replace(" ", '').split(",")
        info['id'] = list(map(int, info['id'].strip().replace(" ", "").split(",")))
        self.janela.destroy()
        bot.Telegram(info["token"], info["canal"], info["id"])

if __name__ == "__main__":
    janela = Tk()
    janela.title("Config")
    Config(janela).mainloop()