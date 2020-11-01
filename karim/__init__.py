import os
from rq import Queue
from worker import conn
from instaclient import InstaClient
from telegram.ext.updater import Updater
from telegram.ext.defaults import Defaults
from telegram.utils.request import Request
from karim.classes.mq_bot import MQBot
from telegram import ParseMode
from telegram.ext import messagequeue as mq

LOCALHOST = True
queue = None
if os.environ.get('PORT') in (None, ""):
    # Code running locally
    LOCALHOST = True
    instaclient = InstaClient()
    if not os.path.exists('karim/bot/persistence'):
        os.makedirs('karim/bot/persistence')
else:
    LOCALHOST = False
    queue = Queue(connection=conn)
    instaclient = InstaClient(host_type=InstaClient.WEB_SERVER)
    

# Initialize Bot
from karim.secrets import secrets
BOT_TOKEN = secrets.get_var('BOT_TOKEN')
URL = secrets.get_var('SERVER_APP_DOMAIN')
PORT = int(os.environ.get('PORT', 5000))
from karim.bot import telebot

# set connection pool size for bot 
request = Request(con_pool_size=8)
q = mq.MessageQueue(all_burst_limit=3, all_time_limit_ms=3000)
telegram_bot = MQBot(BOT_TOKEN, request=request, mqueue=q)
updater = Updater(bot=telegram_bot, use_context=True)

# SET UP BOT COMMAND HANDLERS
telebot.setup(updater)
        

