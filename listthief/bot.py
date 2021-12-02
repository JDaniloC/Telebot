from telethon.tl.functions.messages import GetDialogsRequest
from telethon.errors.rpcerrorlist import PeerIdInvalidError
from telethon.tl.types import InputPeerEmpty
from telethon.sync import TelegramClient
import asyncio, json, traceback
from telethon import events
from messages import *

MAX_CACHE = 10
DATA_PATH = "dados.json"

old_messages = []
reply_chats = []

async def conectar(phone_number, api_id, api_hash):
    client = TelegramClient(phone_number, api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        await client.send_code_request(phone_number)
        await client.sign_in(phone_number, input(ask_for_code()))
    return client

async def enviar_texto(client, message):
    remove_chats = []
    for chat in reply_chats:
        try:
            await client.send_message(
                entity = chat, 
                message = message
            )
        except PeerIdInvalidError:
            print(invalid_id_error(chat))
            remove_chats.append(chat)
        except: traceback.print_exc()
    
    for chat in remove_chats:
        reply_chats.remove(chat)

async def main():
    global reply_chats
    with open(DATA_PATH, encoding = "utf-8") as file:
        data = json.load(file)
        phone_number = data["phone_number"] 
        api_hash = data["api_hash"] 
        pattern = data["pattern"]
        api_id = data["api_id"]

        target_chats = data.get("target_chats", [])
        reply_chats = data.get("reply_chats", [])
        replace = data.get("replace", {})

    client = await conectar(phone_number, api_id, api_hash)
    response = await client(GetDialogsRequest(
        offset_date = None, hash = 0,
        offset_id = 0, limit = 100,
        offset_peer = InputPeerEmpty()))
    
    for chat in response.chats:
        choose = input(choose_chat(chat.title))
        try: choose = int(choose)
        except: choose = -1

        if choose == 0:
            break
        elif choose == 1:
            target_chats.append(chat.id)
        elif choose == 2:
            reply_chats.append(chat.id)
        else:
            continue
    
    @client.on(events.NewMessage(chats = target_chats, pattern = pattern))
    async def handler(event):
        message = event.message.message
        for key, value in replace.items():
            message = message.replace(key, value)
        
        if message not in old_messages:
            old_messages.append(message)
            if len(old_messages) >= MAX_CACHE:
                old_messages.pop(0)
            await enviar_texto(client, message)
    
    print(start_msg(target_chats, reply_chats))
    return client

loop = asyncio.get_event_loop()
client = loop.run_until_complete(main())
client.run_until_disconnected()