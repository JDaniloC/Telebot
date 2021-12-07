from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from cryptography.fernet import Fernet
import json

def get_google_credentials():
    """ Login at Google account and returns the name/email/picture of the user """
    try:
        with open("config/data.dll", encoding = "utf-8") as infos:
            chave = Fernet(b'kwlHwoHHTYbrYV6WyEJR5Hq_8LIhNtnQ0ltntvHcLDg=')
            arquivo = chave.decrypt("".join(infos.readlines()).encode())
            infos = json.loads(arquivo.decode('utf-8'))
    except: pass
    
    flow = InstalledAppFlow.from_client_config(infos,
        scopes=["https://www.googleapis.com/auth/userinfo.profile", 
                "https://www.googleapis.com/auth/userinfo.email", "openid"],
        redirect_uri="http://127.0.0.1:8080/"
    )

    credentials = flow.run_local_server(
        authorization_prompt_message = "Por favor, visite este site: {url}",
        success_message = "Pronto! Você pode fechar esta janela.")

    user_info_service = build('oauth2', 'v2', credentials=credentials)
    user_info = user_info_service.userinfo().get().execute()
    
    return user_info["name"], user_info['email'], user_info['picture']