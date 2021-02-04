import speech_recognition as sr
import subprocess
import os
from pydub import AudioSegment
from pydub.silence import split_on_silence
import shutil
from concurrent import futures


def ffmpeg_convert(ogg_audio, audio_id):
    """
    coroutine for converting the .ogg audios into .wav
    :return tuple
    """
    wav = ogg_audio.replace(".oga", ".wav")
    try:
        process = subprocess.Popen(['ffmpeg', '-i', ogg_audio, wav], shell=True, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
    except subprocess.SubprocessError as e:
        print("Subprocess error:", str(e))
    else:
        process.wait()
    cwd = os.getcwd()
    wav = os.path.join(cwd, wav)
    return wav, audio_id


def deletes(audios):
    """
    deletes the files downloaded and converted from the filesystem
    """
    for audio in audios.values():
        try:
            os.remove(audio)
        except subprocess.SubprocessError as err:
            print("Error:", str(err))


class STT:
    def __init__(self, ogg_audios, folder="audio-chunks"):
        """
        ogg_audios = {audio_id: path_to_ogg}
        """
        self._ogg_audios = dict(ogg_audios)
        self._wav_audios = self.convert_to_wav()
        self._recognizer = sr.Recognizer()
        self.folder = folder

    def cleanup(self):
        """
        deletes folder and files instantiated in the class
        """
        try:
            shutil.rmtree(self.folder)
        except shutil.Error as err:
            print("Error:", str(err))
        else:
            deletes(self._ogg_audios)
            deletes(self._wav_audios)

    def convert_to_wav(self):
        """
        converting the audio (downloaded from telegram) to wav
        :return: dict
        """
        workers = len(self._ogg_audios)
        with futures.ThreadPoolExecutor(workers) as pool:
            res = pool.map(ffmpeg_convert, self._ogg_audios.values(), self._ogg_audios.keys())

        wavs = {}
        for el in res:
            wavs[el[1]] = el[0]
        return wavs

    def get_transcription(self, wav, wav_id):
        """
        executes the audio transcription
        """
        # open the audio file using pydub
        sound = AudioSegment.from_wav(wav)
        # split audio sound where silence is 700 milliseconds or more and get chunks
        chunks = split_on_silence(sound,
                                  min_silence_len=500,
                                  silence_thresh=sound.dBFS - 14,
                                  # keep the silence for 1 second
                                  keep_silence=500,
                                  )
        # create a directory to store the audio chunks
        if not os.path.isdir(self.folder):
            os.mkdir(self.folder)
        whole_text = ""

        # process each chunk
        for i, audio_chunk in enumerate(chunks, start=1):
            # export audio chunk and save it in the `folder_name` directory.
            chunk_filename = os.path.join(self.folder, f"chunk{i}.wav")
            audio_chunk.export(chunk_filename, format="wav")

            # recognize the chunk
            with sr.AudioFile(chunk_filename) as source:
                audio_listened = self._recognizer.record(source)
                # try converting it to text
                try:
                    text = self._recognizer.recognize_google(audio_listened, language="IT")
                except sr.UnknownValueError as e:
                    print("Error:", str(e))
                else:
                    text = f"{text.capitalize()}. "
                    whole_text += text

        return whole_text, wav_id

    def __call__(self, *args, **kwargs):
        """
        executes the transcriptions using a threadpool
        """
        workers = len(self._wav_audios)  # max number of workers is how many audios are there

        with futures.ThreadPoolExecutor(workers) as pool:
            res = pool.map(self.get_transcription, self._wav_audios.values(), self._wav_audios.keys())

        texts = {}  # produce the result as a dict
        for el in res:
            texts[el[1]] = el[0]
        return texts

    def __repr__(self):
        fmt = "Audio: {} in message id: {}\n"
        string = ""
        for message_id in self._ogg_audios:
            string += fmt.format(self._ogg_audios[message_id], message_id)
        return string[:-1]

    def __len__(self):
        return len(self._ogg_audios)

    def __iter__(self):
        return (i for i in self._ogg_audios)

    def __getitem__(self, item):
        return self._ogg_audios[item]

    def __bool__(self):
        return len(self._ogg_audios) != 0

    def __contains__(self, item):
        return item in self._ogg_audios
