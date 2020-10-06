import jsonpickle
from telethon import client
from telethon.errors.rpcerrorlist import FirstNameInvalidError
from karim.classes.persistence import persistence_decorator
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
from telethon.errors.rpcbaseerrors import UnauthorizedError
from karim.bot.commands import *
from karim.classes.callbacks import Callbacks
import math

class Forwarder(SessionManager):
    """Manages requests to the TelegramClient regarding the steps to scrape data from the Telegram API"""
    def __init__(self, method, chat_id, user_id, message_id, phone=None, password=None, code=None, phone_code_hash=None, code_tries=0, selected_ids=[], group_ids=None, group_titles=None, shown_ids=[], text=None, targets=[], rotate_size=6, first_index=0, last_index=None, page_index=1, pages=None):
        """
        groups: List of Dictionaries {id: title}
        selected_ids: Dictionary(id: title)
        shown_groups: Dictionary(id: title)
        """
        SessionManager.__init__(self, method=method, chat_id=chat_id, user_id=user_id, message_id=message_id, phone=phone, password=password, code=code, phone_code_hash=phone_code_hash, code_tries=code_tries)
        self.selected_ids = selected_ids
        self.group_ids = group_ids
        self.group_titles = group_titles
        self.shown_ids = shown_ids
        self.text = text
        self.targets = targets
        self.rotate_size = rotate_size
        self.first_index = first_index
        self.last_index = self.first_index + self.rotate_size
        self.page_index = page_index
        self.pages = pages



    def get_selection(self):
        """Return list()"""
        return self.selected_ids.copy()

    def get_groups(self, titles=False):
        """Return list()"""
        if titles:
            return self.group_titles.copy()
        return self.group_ids.copy()

    def get_groups_dict(self):
        groups = {}
        for index, group in enumerate(self.get_groups()):
            groups[group] = self.group_titles[index]
        return groups

    def get_shown(self):
        """Return list()"""
        return self.shown_ids.copy()

    def get_targets(self):
        """Return list()"""
        return self.targets.copy()

    # Connects to Telegram API
    def scrape_dialogues(self, last_date=None, chunk_size=200):
        """
        Return a list of dicts of dialogues the client is connected to.
        """
        try:
            client = self.connect()
            group_titles = []
            group_ids = []
            chats = client.get_dialogs()
            for chat in chats:
                try:
                    if not chat.is_user:
                        group_ids.append(chat.id)
                        group_titles.append(chat.title)
                except:
                    print('Error')
                    continue
            client.disconnect()
            self.__set_groups(group_ids, group_titles)
            shown_ids = group_ids[self.first_index:self.last_index+1]
            self.__set_shown(shown_ids)
            return self.get_groups()
        except UnauthorizedError:
            raise UnauthorizedError
        except Exception:
            raise Exception

    @persistence_decorator
    def __set_groups(self, group_ids, group_titles):
        """Set group titles and ids"""
        self.pages = math.ceil(len(group_ids)//self.rotate_size)
        self.group_ids = group_ids
        self.group_titles = group_titles

    @persistence_decorator
    def __set_shown(self, shown_ids):
        """
        shown: List of group ids 
        """
        self.shown_ids = shown_ids

    @persistence_decorator
    def set_text(self, text):
        self.text = text
        return self.text

    # MANAGE MARKUP ROTATION AND SELECTIONS
    @persistence_decorator
    def add_selection(self, id):
        """id: group_id"""
        if str(id) in self.selected_ids:
            return Exception
        self.selected_ids.append(id)
        return self.selected_ids.copy()

    @persistence_decorator
    def remove_selection(self, id):
        """id: group_id"""
        self.selected_ids.remove(id)
        return self.selected_ids.copy()

    @persistence_decorator
    def rotate(self, direction):
        if direction == Callbacks.LEFT:
            if self.first_index == 0:
                self.page_index = self.pages
                self.first_index = len(self.group_ids) - self.rotate_size -1
                self.last_index = len(self.group_ids)
            elif self.page_index == 1:
                self.page_index == self.pages
                self.first_index = len(self.group_ids) - self.rotate_size-1
                self.last_index = len(self.group_ids) -1
            else:
                self.page_index -= 1
                self.first_index -= self.rotate_size +1
                self.last_index -= self.rotate_size +1

        elif direction == Callbacks.RIGHT:
            if self.last_index == len(self.group_ids):
                self.page_index = 1
                self.first_index = 0
                self.last_index = self.first_index + self.rotate_size
            elif self.page_index == self.pages-1:
                self.page_index += 1
                self.first_index = self.last_index
                self.last_index = len(self.group_ids)
            elif self.page_index == self.pages:
                self.page_index = 1
                self.first_index = 0
                self.last_index = self.first_index + self.rotate_size
            else:
                self.page_index += 1
                self.first_index += self.rotate_size+1
                self.last_index += self.rotate_size+1
        print('First Index: ', self.first_index)
        print('Last Index: ', self.last_index)
        shown = self.group_ids[self.first_index:self.last_index+1]
        self.__set_shown(shown)
        return self.get_shown()

    # GET PARTICIPANTS AND SEND MESSAGE
    def send(self):
        count = 0
        fail = 0
        client = self.create_client(self.user_id)
        try:
            # LOAD CHATS
            client = self.connect(client)
            groups = []
            chats = client.get_dialogs()
            for chat in chats:
                if str(chat.id) in self.get_selection():
                    groups.append(chat)
            # LOAD & SCRAPE TARGETS
            targets = self.__load_targets(client, groups)
            # SEND MESSAGES
            for target in targets:
                try:
                    client.send_message(target, self.text)
                    count += 1
                except:
                    fail += 1
                    continue
            client.disconnect()
            return [count, fail]
        except UnauthorizedError:
            raise UnauthorizedError
        

    def __load_targets(self, client, groups):
        targets = []
        for group in groups:
            members = self.__scrape_participants(group, client)
            for member in members:
                if member.id not in targets:
                    targets.append(member)
        return  targets

    # Connects to Telegram API
    def __scrape_participants(self, target_group, client):
        """
        Returns a list of all participants of a selected_ids group or channel
        """
        try:
            all_participants = client.get_participants(target_group, aggressive=True)
            return all_participants
        except UnauthorizedError:
            raise UnauthorizedError
            


            





    
            



       
