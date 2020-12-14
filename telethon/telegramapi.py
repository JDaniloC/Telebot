from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *
from selenium.webdriver import Chrome

from tkinter import *
import time

def captura_id_hash(numero):
    browser = Chrome("chromedriver")
    browser.get("https://my.telegram.org/auth")
    wait = WebDriverWait(browser, 120)

    # Coloca o número
    wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, 'input[id="my_login_phone"]')
    )).send_keys(numero)
    browser.find_element_by_css_selector(
        "div[class='support_submit'] button"
    ).click()
    
    # Entra no /apps
    development = wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "a[href='/apps']")))
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

