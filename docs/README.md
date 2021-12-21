# Telebot 2
    
> Telegram bots to invite people from mega groups and channels and so on.

<p align="center">
  <img alt="Main page" src="./telebot2-main.png" width = "100%">
</p>

This repository is a collection of telegram bots that can invite people, send programmed messages, copy messages and so on. Important to note: **The limit of add each day is 40**, more than it will be blocked by spam.

 - [x] Google OAuth 2.0 and [licensor](https://github.com/JDaniloC/Individual-Licenciador) integration.
 - [x] Can get the telegram API and Hash ID automatically from given number.
 - [x] Can send messages to each contact from a group or channel.
 - [x] There are settings to avoid spam block: Interact with X people with Y seconds between them.
 - [x] Logs field and catalogued errors with easy understanding.
 - [x] Created using Eel to connect async python to HTML/CSS/JS interface.

## How to use

Install python 3.7 or above, and run the followed command to install the dependencies.

`pip install requirements.txt`

So you can enter in the folders to run: `python bot.py` or `python telebot.py`

Run `python -m eel telebot.py web -F -w -i web/images/favicon.ico` to compile the telebot2.

## Telebot v.1

<img alt="Telebot version 1" src="./telebot1.png" width = "50%" align = "left">

The first version of telebot, where can add, send messages, files (images, audio or video), with the same settings as the second version, but built using TKinter, and the "logs panel" is the terminal, it's used if the telebot2 doesn't add no one.

>> Different from 2° version: Licensor found in admin/ folder generates a file with the license days.

 - Sleep for X seconds after add settings.
 - Skip the first X contacts from the group.
 - Add only contacts was online in the last X days.
 - Only add X contacts in this session.

> At least 10k contacts are added in two groups using this version, through more than 10 telegram accounts.

## Other bots

<img alt="Group list" src="./listsender.png" width = "50%" align = "right">

### MetaSender
Reads the MQL return file and sends the messages to X groups, sends a parcial result (with tendency analysis like SMA, RSI and the closest support/resistance) and full result when the trades are completed.

### ListSender
Can program a list of trades to be sent to X groups with 5min of before the trade, sends a parcial (with tendency analysis like SMA, RSI and the closes support/resistance) and full result when the trades are completed, verify if the asset is open before start the trade, can specify a lot of lists simultaneous till 2 Gales and M30.

The commands are:
- Registrar nova lista: Register a new list.
- Ver listas registradas: Shows the lists registered.
- Começar transmissão: Start the transmission from the register list.
- Parar transmissão: Stop the transmission from the transmission list.
- Adicionar novo grupo: Ready the bot to wait the user put the bot in a new group to add in the queue of groups to send the messages. 
- Desligar bot: Get out from the loop, exiting the bot.

### 

<p align="center">
    <img alt="Group list" src="./telebot2-groups.png" width = "100%">
    <img alt="Adding" src="./telebot2-label.png" width = "100%">
</p>
