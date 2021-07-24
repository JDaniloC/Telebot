from cryptography.fernet import Fernet
import time

key = b'5oa6VUCRinbN50aH5XT7gOfrbdCeOaEUembWDV3EIW4='

total = int(input("Digite o valor de licenças: "))

f = Fernet(key)
with open('license', 'wb') as file:
    message = f"{time.time()}|0|{total}"
    result = f.encrypt(message.encode())
    file.write(result)