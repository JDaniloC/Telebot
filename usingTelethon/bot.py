from tkinter import *
import json, asyncio, sys
from scraper import main

class Interface(Frame):
    def __init__(self, janela):
        super().__init__(janela)
        self.janela = janela
        self.pack(fill=X, padx=5, pady=5)
        self.widgets()

    def widgets(self):
        self.entradas = []
        titulos = ["App api_id", "App api_hash", "Phone number"]

        for i in range(0, 20, 2):            
            api_id = StringVar()
            api_hash = StringVar()
            number = StringVar(value = "+55")

            client = {
                "id": api_id,
                "hash": api_hash,
                "number": number
            }
            variaveis = [api_id, api_hash, number]

            for index, titulo in enumerate(titulos):
                Label(self, text = titulo).grid(row = i, column = index)
                campo = Entry(self, textvariable = variaveis[index])
                if i > 1:
                    campo.config(state = 'disabled')
                campo.grid(row = i + 1, column = index)
            self.entradas.append(client)

        self.pausar = BooleanVar(value = True)
        Checkbutton(self, text = "Pausar?", variable = self.pausar).grid(row = 22, columnspan = 2)
        Button(self, text = "Extrair", command = self.comecar).grid(row = 22, column = 1, columnspan = 2)
        # self.carregar()

    def carregar(self):
        try:
            with open("dados.json", "r+") as file:
                dados = json.load(file)
            for index, dado in enumerate(dados):
                for key, value in dado.items():
                    self.entradas[index][key].set(str(value))
        except: 
            pass

    def comecar(self):
        resultado = []
        for client in self.entradas:
            if client['id'].get() != "":
                client = {key:value.get() for key, value in client.items()}
                client['id'] = int(client['id'])
                resultado.append(client)
        # with open("dados.json", "w") as file:
        #     json.dump(resultado, file)

        self.janela.destroy()
        pausar = self.pausar.get()

        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(main(resultado, pausar))
        except Exception as e:
            print(e)
        
        input("Programa finalizado")

janela = Tk()
janela.title("Extrator de membros")
program = Interface(janela)
program.mainloop()