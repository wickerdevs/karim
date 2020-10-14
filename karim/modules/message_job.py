from rq.job import Retry
from telethon.errors.rpcerrorlist import PeerFloodError
from karim import queue, LOCALHOST
from karim.bot.texts import *
from karim.secrets import secrets
from karim.classes.mq_bot import MQBot
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import asyncio, time, redis, os


def create_client(user_id, bot=False):
    """Creates and returns a TelegramClient"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    api_id = secrets.get_var('API_ID')
    api_hash = secrets.get_var('API_HASH')
    # TODO
    # proxy=(socks.SOCKS5, '127.0.0.1', 4444)
    if LOCALHOST:
        session = 'karim/bot/persistence/{}'.format(user_id)
    else:
        session_string = os.environ.get('session:{}'.format(user_id))
        if not session_string:
            try:
                # Falling Back to RedisSession
                print('LOADING REDIS SESSION')
                connector = redis.from_url(os.environ.get('REDIS_URL'))
                string = connector.get('session:{}'.format(user_id))
                print('SESSION STRING OUTPUTTED')
                if string:
                    # Session is stored in Redis
                    decoded_string = string.decode("utf-8") 
                    session = StringSession(decoded_string)
                else:
                    session = StringSession()
                connector.close()
            except Exception as error:
                # No Session Error
                print('Error in session_manager.create_client(): ', error)
                raise error
        else:
            try:
                session = StringSession(session_string)
            except Exception as error:
                print('Error in session_manager.create_client(): ', error)
                raise error
    try:
        client = TelegramClient(session, api_id, api_hash, loop=loop).start(bot_token=os.environ.get('BOT_TOKEN')) #proxy = proxy
    except Exception as error:
        print('Error in session_manager.create_client(): ', error)
        raise error
    print('TELEGRAM CLIENT WITH SESSION CREATED')
    return client


def send_message(user_id, target, index, targets_len, telethon_text):
    client = create_client(user_id)
    bot_client = create_client('bot', bot=True)
    client.connect()
    bot_client.connect()
    messages = client.get_messages(bot_client.get_me().username, limit=1, from_user=bot_client.get_me())
    message = messages[0]
    # Get Message:
    try:
        client.send_message(target, telethon_text)
        bot_client.edit_message(user_id, message=message, text=sending_messages_text.format(len(targets_len), index))
        time.sleep(35)
    except PeerFloodError as error:
        print('PeerFloodLimit reached. Account may be restricted or blocked: ', error)
    except Exception as error:
        print('Error in sending message ', error)
    client.disconnect()
    bot_client.disconnect()


def queue_messages(targets, context, forwarder, client=None):
    failed = []
    success = 0
    for index, target in enumerate(targets):
        print('TARGET: ', target)
        if target not in (forwarder.user_id, context.bot.id,):
            queue.enqueue(send_message, user_id=forwarder.user_id, target=target, index=index, targets_len=len(targets), telethon_text=forwarder.telethon_text, retry=Retry(max=2, interval=[35, 45]))
        
    client.disconnect()
    return success