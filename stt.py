import audioop
import time
from contextlib import contextmanager
from ctypes import CFUNCTYPE, c_char_p, c_int, cdll
from threading import Thread

import numpy as np
import pyaudio
import pylab
import speech_recognition as sr

CHUNK = 8000
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
THRESHOLD = 600
SILENCE_DETECTION = 1.5
LISTENING = False


class GoogleSpeechRecognizer:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.__class__.finished = False

    @classmethod
    def set_finished(self, finished):
        self.finished = True

    def reset(self):
        self.__class__.finished = False

    def recognize(self, va):
        with noalsaerr():
            p = pyaudio.PyAudio()

        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            output=True,
            frames_per_buffer=CHUNK
        )

        try:
            data = stream.read(CHUNK)
            audio = None
            while data != '':
                rms = audioop.rms(data, 2)
                if rms >= THRESHOLD:
                    audio = data
                    silence_counter = 0
                    while silence_counter < SILENCE_DETECTION:
                        data = stream.read(CHUNK)
                        if LISTENING:
                            stream.write(data, CHUNK)
                        audio = audio + data

                        rms = audioop.rms(data, 2)
                        if rms < THRESHOLD:
                            silence_counter += 1
                        else:
                            silence_counter = 0

                    stream.stop_stream()

                    audio_data = sr.AudioData(
                        audio, RATE, p.get_sample_size(FORMAT))
                    try:
                        com = self.recognizer.recognize_google(audio_data)
                        t = Thread(target=va.command, args=(com,))
                        t.start()
                        t.join()
                    except sr.UnknownValueError:
                        print('Google Speech Recognition could not understand audio')
                    except sr.RequestError as e:
                        print(f'Could not request results from Google Speech Recognition service; {e}')

                    stream.start_stream()
                    self.reset()

                data = stream.read(CHUNK)
                if LISTENING:
                    stream.write(data, CHUNK)
        except KeyboardInterrupt:
            stream.stop_stream()
            stream.close()
            p.terminate()
            raise KeyboardInterrupt


ERROR_HANDLER_FUNC = CFUNCTYPE(
    None, c_char_p, c_int, c_char_p, c_int, c_char_p)


def py_error_handler(filename, line, function, err, fmt):
    pass


c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)


@contextmanager
def noalsaerr():
    asound = cdll.LoadLibrary('libasound.so')
    asound.snd_lib_error_set_handler(c_error_handler)
    yield
    asound.snd_lib_error_set_handler(None)


if __name__ == '__main__':
    recognizer = GoogleSpeechRecognizer()
    recognizer.recognize()
