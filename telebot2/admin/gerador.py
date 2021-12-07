from cryptography.fernet import Fernet
import json

chave = Fernet(b'kwlHwoHHTYbrYV6WyEJR5Hq_8LIhNtnQ0ltntvHcLDg=')

infos = json.dumps({"web":{"client_id":"278925362376-j96fnrbrj19plth2f6lm0cgbo218uf4g.apps.googleusercontent.com","project_id":"spartan-avenue-329102","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_secret":"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","redirect_uris":["https://developers.google.com/oauthplayground","http://127.0.0.1:8080/"]}}).encode()


with open('../config/data.dll', 'w', encoding='utf-8') as file:
    file.write(chave.encrypt(infos).decode('utf-8'))