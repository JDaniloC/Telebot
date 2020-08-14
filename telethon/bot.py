try:
    import selenium
except:
    print("Instalando dependencia...")
    from subprocess import call
    call(['pip', 'install', 'selenium'])

from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from tkinter import *
from tkinter import ttk as t
from tkinter import messagebox
from tkinter.filedialog import askopenfilename
import json, asyncio, sys, time
from scraper import main
from datetime import datetime

def captura_id_hash(numero):
    browser = Chrome("chromedriver")
    browser.get("https://my.telegram.org/auth")
    wait = WebDriverWait(browser, 120)

    # Coloca o número
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[id="my_login_phone"]'))).send_keys(numero)
    browser.find_element_by_css_selector("div[class='support_submit'] button").click()
    
    # Entra no /apps
    development = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='/apps']")))
    time.sleep(1)
    development.click()

    try:
        # Prenche os campos e entra clica em salvar
        title = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[id='app_title']")))
        title.send_keys("GroupTaker")

        browser.find_element_by_css_selector("input[id='app_shortname']").send_keys("group")
        browser.find_element_by_css_selector("input[value='other']").click()
        browser.find_element_by_css_selector("button[id='app_save_btn']").click()
    except:
        pass

    # Pega o ID/Hash
    app_id = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'span[class="form-control input-xlarge uneditable-input"]')))
    app_hash = browser.find_elements_by_css_selector('span[class="form-control input-xlarge uneditable-input"]')[1]

    dados = {
        "id": int(app_id.text),
        "hash": app_hash.text,
        "number": numero
    }

    browser.close()

    return dados


class Interface(Frame):
    def __init__(self, janela):
        super().__init__(janela)
        self.janela = janela
        self.esquerda = t.Label(self)
        self.direita = t.Label(self)

        self.esquerda.pack(side = LEFT)
        self.direita.pack(side = LEFT, padx = 5)
        self.pack(fill=X, padx=5, pady=5)
        self.widgets()

    def seleciona_arquivo(self):
        self.media.delete(0, END)
        self.media.insert(0, askopenfilename())

    def widgets(self):

        self.texto = Text(self.direita, width = 50, height = 30)
        self.texto.pack(expand = True)
        opcoes = t.Label(self.direita)
        opcoes.pack()

        self.media = t.Entry(opcoes)
        self.isAudio = BooleanVar(value = False)
        self.media.pack(side = LEFT)
        t.Button(
            opcoes, text = "Inserir arquivo", command = self.seleciona_arquivo
        ).pack(side = LEFT)
        t.Checkbutton(
            opcoes, text = "É áudio/vídeo", variable = self.isAudio
        ).pack(side = LEFT)

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
                t.Label(self.esquerda, text = titulo).grid(row = i, column = index)
                campo = t.Entry(self.esquerda, textvariable = variaveis[index])
                # Comentar na versão paga
                # if i > 1:
                #     campo.config(state = 'disabled')
                campo.grid(row = i + 1, column = index)
            self.entradas.append(client)
        
        self.pausar = StringVar(value = "0")
        self.pular = StringVar(value = "0")
        self.modo = StringVar(value = "add")
        
        t.Label(self.esquerda, text = "Pausa (segundos):"
            ).grid(row = 23, column = 0)
        t.Entry(self.esquerda, textvariable = self.pausar, 
            width = 5).grid(row = 23, column = 0, columnspan = 3)
        t.Label(self.esquerda, text = "Pular:").grid(
            row = 23, column = 1, columnspan = 2)
        t.Entry(self.esquerda, textvariable = self.pular, width = 5
            ).grid(row = 23, column = 2, columnspan = 3)
        t.Radiobutton(self.esquerda, text = "Adição", 
            variable = self.modo, value = "add").grid(
            row = 24, column = 0)
        t.Radiobutton(self.esquerda, text = "Mensagem", 
            variable = self.modo, value = "msg").grid(
            row = 24, column = 1)
        t.Radiobutton(self.esquerda, text = "Captura", 
            variable = self.modo, value = "save").grid(
            row = 24, column = 2)

        self.limitar = BooleanVar(value = False)
        t.Checkbutton(self.esquerda, text = "Limitar", 
            variable = self.limitar).grid(
            row = 25, column = 0)
        t.Button(self.esquerda, text = "Começar", 
            command = self.comecar).grid(
            row = 25, columnspan = 3, pady = 5)
        # Comentar na versão trial
        self.carregar()

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
            elif len(client['number'].get()) > 3:
                client = captura_id_hash(client['number'].get())
                resultado.append(client)
        
        # Comentar essa parte para a versão trial
        # with open("dados.json", "w") as file:
        #     json.dump(resultado, file, indent = 2)

        # Fazer o botão pausar e ter opção mandar mensagem
        try:
            pausar = int(self.pausar.get())
            pular = int(self.pular.get())
        except:
            messagebox.showinfo("Error", 
                "Tempo de espera e quantidade de pessoas para pular precisam ser números")
            return

        mensagem = {
            "msg": self.texto.get(1.0, END),
            "path": self.media.get(), 
            "audio": self.isAudio.get()
        }
        limitar = self.limitar.get()

        self.janela.destroy()
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(main(
                resultado, pausar, self.modo.get(), pular, mensagem, limitar))
        except Exception as e:
            print(e)
        
        input("Programa finalizado")

final = datetime(2020, 9, 1, 0, 0)
restante = final - datetime.now()
if final.timestamp() - datetime.now().timestamp() > 0:
    print(str(restante).replace("days", "dias"))
    janela = Tk()
    janela.title("TelegramBot")
    program = Interface(janela)
    program.mainloop()
else:
    input("O período teste acabou.")