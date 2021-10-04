def choose_chat(chat_title):
    return f"""O grupo: {chat_title}
    [0] - Começar o bot
    [1] - Capturar (ver as mensagens)
    [2] - Enviar as mensagens
    """

def ask_for_code(phone_number):
    return f"Digite o código recebido em {phone_number}: "

def start_msg(target_chats, reply_chats):
    return f"""
    Bot iniciado, buscando mensagens em {len(target_chats)} grupos e mandando para {len(reply_chats)} grupos.
    """

def invalid_id_error(_id):
    return f"""Não consigo enviar para o grupo com ID: {_id}!"""