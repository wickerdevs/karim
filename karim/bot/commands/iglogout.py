from karim.bot.commands import *
from karim import instaclient 

@run_async
@send_typing_action
def instagram_log_out(update, context):
    if check_auth(update, context):
        # User is authorised
        message = update.effective_chat.send_message(text=logging_out)
        result = instaclient.logout()
        if result:
            message.edit_text(text=instagram_loggedout_text)
        else:
            message.edit_text(text=error_loggingout_text)
    else:
        update.effective_chat.send_message(text=not_admin_text)