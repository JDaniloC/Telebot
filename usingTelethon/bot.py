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
from tkinter import messagebox
import json, asyncio, sys, time
from scraper import main

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

    # Salva o resultado
    with open("dados.json") as file:
        lista = json.load(file)

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
                # if i > 1:
                #     campo.config(state = 'disabled')
                campo.grid(row = i + 1, column = index)
            self.entradas.append(client)

        self.pausar = StringVar(value = "0")
        Label(self, text = "Tempo de pausa (em segundos):").grid(row = 22, column = 0, columnspan = 2)
        Entry(self, textvariable = self.pausar, width = 10).grid(row = 22, column = 1, columnspan = 2)
        Button(self, text = "Extrair", command = self.comecar).grid(row = 22, column = 2, columnspan = 3)
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
            elif client['number'].get() != "+55":
                client = captura_id_hash(client['number'].get())
                resultado.append(client)
        
        # Comentar essa parte para a versão trial
        with open("dados.json", "w") as file:
            json.dump(resultado, file, indent = 2)

        # Fazer o botão pausar e ter opção mandar mensagem
        try:
            pausar = int(self.pausar.get())
        except:
            messagebox.showinfo("Tempo de espera", "Precisa ser um número")
            return

        self.janela.destroy()
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