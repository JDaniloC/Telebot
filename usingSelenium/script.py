from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, json

def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    """
    TAKEN FROM https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()

def info_grupo(alvo):
    contatos = browser.find_elements_by_css_selector("a > div.im_dialog_message_wrap > div.im_dialog_peer > span")
    
    for contato in contatos:
        if alvo in contato.text:
            contato.click()
            time.sleep(2)
            browser.find_element_by_css_selector("[ng-click='showPeerInfo()']").click() 

def captura_nicknames(nome_grupo):
    info_grupo(nome_grupo)
    contador = -1
    lista = browser.find_elements_by_css_selector("a.md_modal_list_peer_name")
    resultado = []
    for pessoa in lista:
        # Pula o próprio nome
        if contador == -1:
            contador += 1
            continue

        pessoa.click()
        try:
            time.sleep(0.1)
            nick = browser.find_element_by_css_selector("div[ng-if='user.username'] span")
            if "bot" not in nick.text and nick.text != "":
                print(f"Capturei {nick.text}")
                resultado.append(nick.text)
                contador += 1
            if contador == 300:
                break
        except:
            pass
        finally:
            fechar = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".user_modal_window a")
                ))
            fechar.click()
    browser.find_element_by_css_selector(".chat_modal_window a").click()
    
    return resultado

def adiciona_novo_contato(nick):
    browser.find_element_by_css_selector("[ng-click='inviteToGroup()']").click()
    entrada = browser.find_element_by_css_selector(".contacts_modal_search_field")
    entrada.send_keys(nick)
    contato = wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "a.contacts_modal_contact")
            ))
    contato.click()
    entrada.clear()
    browser.find_element_by_css_selector("[ng-click='submitSelected()']").click()

with open("config.json", encoding= "UTF-8") as file:
    config = json.load(file)
    NUMBER_PHONE = config["number"]
    AIM_GROUP = config["from"]
    GOAL_GROUP = config["to"]

# ENTRAR E AUTENTICAÇÃO

browser = Chrome("chromedriver.exe")
browser.get("https://web.telegram.org/")
wait = WebDriverWait(browser, 10)

numero = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[name=phone_number]")))
numero.send_keys(NUMBER_PHONE)

browser.find_element_by_css_selector(".login_head_submit_btn").click()
browser.find_element_by_css_selector("button[ng-switch=type]").click()

print("Coloque o código do telegram")
printProgressBar(0, 30, prefix = 'Progress:', suffix = 'Complete', length = 50)
for i in range(30):
    # Do stuff...
    time.sleep(1)
    # Update Progress Bar
    printProgressBar(i + 1, 30, prefix = 'Progress:', suffix = 'Complete', length = 50)

wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a > div.im_dialog_message_wrap > div.im_dialog_peer > span")))
# CAPTURA DE DADOS

with open("nicks.json") as file:
    lista_nicks = json.load(file)

print(f"Número de pessoas: {len(lista_nicks)}")

# print("\nCaptrando nicknames...")
# lista_nicks = captura_nicknames(AIM_GROUP)
# print("Captura finalizada")

# with open("nicks.json", "w") as file:
#     json.dump(lista_nicks, file)
#     print("Lista de nicks guardada no nicks.json")

# ADICIONAR MEMBROS
info_grupo(GOAL_GROUP)
print("\nAdicionando contatos")
for nick in lista_nicks:
    try:
        adiciona_novo_contato(nick)
    except:
        acesso_negado = browser.find_elements_by_css_selector(".error_modal_window button.btn-md")
        if acesso_negado != []:
            acesso_negado[0].click()
        try:
            browser.find_element_by_css_selector(".contacts_modal_window .md_modal_action_close").click()
        except:
            pass
    try:
        browser.find_element_by_css_selector("[ng-click='showPeerInfo()']").click() 
    except:
        pass
print("Adição finalizada")
