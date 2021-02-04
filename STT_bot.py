from TelegramApp import TelegramApp, MAX_CONCUR
import STT
from telegram.ext import Updater, CommandHandler, JobQueue


class STTBot:
    def __init__(self, api_id, api_hash, phone, username, token, chat_id, user_set=None, command_name="audio",
                 dialog_limit=20, history_limit=15, interval=30):
        self._app = TelegramApp(api_id, api_hash, phone, username, token, chat_id, user_set, dialog_limit)
        self._history_limit = history_limit
        self.interval = interval
        self._previous_results = set()  # used for caching results to avoid repetitions
        self.command_name = command_name
        self._token = token

    def process_audios(self):
        """
        iterating through the dialogs we get the audio transcription and send it to us with our bot
        """
        results = self._app.print_dialogs(self._history_limit)
        for user in results:
            to_do_messages = []
            for message in results[user]:
                if "mime_type='audio/ogg'" in str(message):
                    if message.id in self._previous_results:
                        # skipping message if we have processed it already
                        print("message from {} already sent, skipping to next...".format(user))
                        continue
                    # removing some items from cache (supposedly the oldest messages)
                    if len(self._previous_results) > 30:
                        for i in range(10):
                            self._previous_results.remove(min(self._previous_results))
                    self._previous_results.add(message.id)  # caching
                    to_do_messages.append(message)
            if not to_do_messages:
                continue
            try:
                audios = self._app.do_download(to_do_messages, MAX_CONCUR)

                sr = STT.STT(audios)
                messages_to_send = sr()

                for message_id in messages_to_send:
                    messages_to_send[message_id] = "Audio from: {}\n{}".format(user, messages_to_send[message_id])

                for key in sorted(messages_to_send.keys()):
                    self._app.send_message(messages_to_send[key], False)
                sr.cleanup()
            except Exception as e:
                print("processing audio failed with exception:", e)
                try:
                    sr.cleanup()
                except UnboundLocalError:
                    pass

    def bot_audio_on_command(self, bot, job):
        """
        function executed by the bot when command is sent
        """
        import time
        t0 = time.time()
        self.process_audios()
        print(time.time() - t0)

    def bot_audio_repeat(self, context):
        """
        function executed by the bot on repeated intervals
        """
        self.process_audios()

    def bot_command(self):
        """
        creating the bot instructions
        """
        updater = Updater(self._token, use_context=True)
        dp = updater.dispatcher
        job_queue = JobQueue()
        job_queue.set_dispatcher(dp)
        # repeats the command on repeat
        job_queue.run_repeating(self.bot_audio_repeat, interval=self.interval * 60)  # repeated intervals
        # creates the handle for the command
        dp.add_handler(CommandHandler(self.command_name, self.bot_audio_on_command))  # command

        updater.start_polling()
        job_queue.start()
        updater.idle()

    def __call__(self, *args, **kwargs):
        self._app.run()
        self.bot_command()
