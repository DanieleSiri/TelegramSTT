# TelegramSTT
Speech to text app for Telegram made with python.

This app allows you to create your own Telegram bot which reads your conversations and translates all the audio messages into text, sending it to you.
It's based on the telethon, speech recognition and pydub modules.

## Prerequisites
requires ffmpeg to be installed and added to path
##### install fmmpeg:
- [on windows](http://blog.gregzaal.com/how-to-install-ffmpeg-on-windows/)
- [on linux](https://www.tecmint.com/install-ffmpeg-in-linux/)
- [on macos](https://superuser.com/questions/624561/install-ffmpeg-on-os-x)

##### telegram requirements:
1. Get the app registered to the Telegram API to get your api hash and api id
2. Get your bot token
3. Start a chat with your bot and get the chat_id from the url request
