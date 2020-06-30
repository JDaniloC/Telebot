from selenium.webdriver import Chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

browser = Chrome("chromedriver")
browser.get("https://my.telegram.org/auth")
wait = WebDriverWait(browser, 80)

input("Funcionou? Clique Enter para finalizar")
