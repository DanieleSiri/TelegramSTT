from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import requests
from telethon.tl.functions.messages import GetDialogsRequest, GetHistoryRequest
from telethon.tl.types import InputPeerEmpty, InputPeerUser, PeerUser
import asyncio


MAX_CONCUR = 30


def callback(current, total):
    # shows download progress
    print('Downloaded', current, 'out of', total,
          'bytes: {:.2%}'.format(current / total))


class TelegramApp:
    def __init__(self, api_id, api_hash, phone, username, token, chat_id, user_set=None, dialogs_limit=20):
        """
        requires telegram api id, hash, the user's phone number, username, the bot token and the chat id with the bot
        (in order for the bot to send messages directly to the user). User_set is used to limit the chat search to
        certain users, and dialogs_limit is used to limit the number of chats to be searched.
        """
        self._client = TelegramClient('session', api_id, api_hash)
        self._phone = phone
        self._username = username
        self._token = token
        self._chat_id = chat_id
        self._url = f'https://api.telegram.org/bot{token}/sendMessage'
        self._get_dialogs = GetDialogsRequest(
            offset_date=None,
            offset_id=0,
            offset_peer=InputPeerEmpty(),
            limit=dialogs_limit,
            hash=0)
        self._user_set = set(user_set) if user_set is not None else None  # must be telegram usernames (e.g. @Username)

    async def start(self):
        """
        starts the bot (effectively does the first time setup if the app has not already been authorized)
        """
        if not await self._client.is_user_authorized():
            await self._client.send_code_request(self._phone)
            try:
                await self._client.sign_in(self._phone, input('Enter the code: '))
            except SessionPasswordNeededError:
                await self._client.sign_in(password=input('Password: '))
        print("bot initialized")

    def send_message(self, message, disable):
        """
        sends a message
        :param message: str
        :param disable: bool
        """
        data = {'chat_id': self._chat_id, 'text': message, 'disable_notification': disable}
        try:
            requests.post(self._url, data).json()
        except Exception as e:
            print(e)

    async def get_dialogs(self):
        """
        returns all the user chats
        """
        dialogs = await self._client(self._get_dialogs)
        return dialogs

    async def get_history(self, get_history):
        """
        returns all the user messages
        """
        history = await self._client(get_history)
        return history

    def print_dialogs(self, history_limit=15):
        """
        returns a dictionary{user: messages} listing all the messages from a specified user set (created at __init__)
        :return: dict
        """
        message_dict = {}
        with self._client:
            dialogs = self._client.loop.run_until_complete(self.get_dialogs())  # gets the chats
        users = {u.id: u for u in dialogs.users}

        for dialog in dialogs.dialogs:
            peer = dialog.peer
            # analyzes only chats with users and not groups or channels
            if isinstance(peer, PeerUser):
                id = peer.user_id
                user = users[id]
                access_hash = user.access_hash
                username = user.username
                name = "{0} {1}".format(str(user.first_name), str(user.last_name) if user.last_name is not None else '')
                if self._user_set is not None:  # if user set not specified, analyzes all the chats
                    # else it skips the ones that are not in user set
                    if username not in self._user_set:
                        continue
                input_peer = InputPeerUser(id, access_hash)
                get_history = GetHistoryRequest(
                    peer=input_peer,
                    offset_id=0,
                    offset_date=None,
                    add_offset=0,
                    limit=history_limit,
                    max_id=0,
                    min_id=0,
                    hash=0)
                with self._client:
                    history = self._client.loop.run_until_complete(self.get_history(get_history))
                messages = history.messages
                message_dict[name] = messages
        if message_dict:
            return message_dict
        else:
            raise NoMessagesFound

    def run(self):
        """
        executes the coroutine to start the app
        """
        with self._client:
            self._client.loop.run_until_complete(self.start())

    async def get_download(self, message, semaphore):
        """
        downloads audio returning the path
        """
        with await semaphore:
            path = await self._client.download_media(message, progress_callback=callback)
        return path, message.id

    async def download_audio(self, messages, concur_req):
        """
        executes coroutine get_download
        """
        path = {}
        semaphore = asyncio.Semaphore(concur_req)
        # instantiates the coroutines for downloading concurrently
        to_do = [self.get_download(message, semaphore) for message in messages]
        to_do_iter = asyncio.as_completed(to_do)
        for future in to_do_iter:
            res, message_id = await future
            path[message_id] = res
        return path

    def do_download(self, messages, concur_req):
        """
        executes the coroutines for the download
        """
        with self._client:
            coro = self.download_audio(messages, concur_req)
            paths = self._client.loop.run_until_complete(coro)
        return paths


class NoMessagesFound(Exception):
    def __init__(self, message="Could not find any messages"):
        self.message = message
        super().__init__(self.message)
