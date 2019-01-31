import contextlib
import inspect
import mimetypes
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid
from multiprocessing import Pool
from random import randint

import metadata_parser
from win10toast import ToastNotifier

from tts import Synthesizer

try:
    import cStringIO
except ImportError:
    import io as cStringIO

FNULL = open(os.devnull, 'w')

toaster = ToastNotifier()


class TextToAction:
    def __init__(self, args):
        pass

    def execute(self, cmd='', msg='', speak=False, duration=0):
        """
        Method to execute the given bash command and display a desktop environment independent notification.
        """
        self.speak = speak
        if self.speak:
            self.say(msg)
        try:
            subprocess.Popen(['notify-send', 'Jon Snow', msg])
        except BaseException:
            pass
        if cmd != '':
            time.sleep(duration)
            try:
                subprocess.Popen(cmd, stdout=FNULL, stderr=FNULL)
            except BaseException:
                pass
        return msg

    def notify(self, title='Jon Snow', msg='', speak=False, duration=0):
        """
        Method to display a desktop environment independent notification on Windows
        """
        self.speak = speak
        if self.speak:
            self.say(msg)
        try:
            toaster.show_toast(title=title, msg=msg, duration=duration)
        except BaseException:
            pass
        return msg

    def say(self, msg, dynamic=False, end=False, cmd=None):
        """
        Method to give text-to-speech output, print the response into console
        """
        if len(msg) < 10000:
            (columns, _) = shutil.get_terminal_size()
            if dynamic:
                if end:
                    print(msg.upper())
                    print(columns * '_' + '\n')
                else:
                    print(f"Jon Snow: {msg.upper()}")
            else:
                print(f"Jon Snow: {msg.upper()}")
                print(columns * '_' + '\n')
        syn = Synthesizer(rate=150)
        msg = ''.join([i if ord(i) < 128 else ' ' for i in msg])
        syn.run(msg)
        return msg

    def pretty_print_nlp_parsing_result(self, doc):
        if len(doc) > 0:
            print('')
            print(f'{"TEXT":12}  {"LEMMA":12}  {"POS":12}  {"TAG":12}  {"DEP":12}  {"SHAPE":12}  {"ALPHA":12}  {"STOP":12}')
            for token in doc:
                print(f'{token.text:12}  {token.lemma_:12}  {token.pos_:12}  {token.tag_:12}  {token.dep_:12}  {token.shape_:12}  {token.is_alpha:12}  {token.is_stop:12}')
            print('')


@contextlib.contextmanager
def nostdout():
    """
    Method to suppress the standard output. (use it with 'with' statements)
    """
    save_stdout = sys.stdout
    sys.stdout = cStringIO.StringIO()
    yield
    sys.stdout = save_stdout


@contextlib.contextmanager
def nostderr():
    """
    Method to suppress the standard error. (use it with 'with' statements)
    """
    save_stderr = sys.stderr
    sys.stderr = cStringIO.StringIO()
    yield
    sys.stderr = save_stderr


def tts_kill():
    """
    Method to kill/end the text-to-speech output immediately.
    """
    subprocess.call(['pkill', 'flite'], stdout=FNULL, stderr=FNULL)


def omniscient_coefficient_optimizer():
    from omniscient import Omniscient
    import spacy

    dataset = [
        ('Where is the Times Square', ['New York City']),
        ('What is the height of Burj Khalifa', ['828 m']),
        ('Where is Burj Khalifa', ['Dubai']),
        ('What is the height of Great Pyramid of Giza', ['480.6 ft']),
        ('Who is playing Jon Snow in Game of Thrones', ['Kit Harington']),
        ('What is the atomic number of oxygen', ['8']),
        ('What is the official language of Japan', ['Japanese']),
        ('What is the real name of Iron Man', ['Tony', 'Stark', 'Tony Stark']),
        ('Who is the conqueror of Constantinople', ['Mehmed II', 'Mehmet II', 'Mehmet']),
        ('When Constantinople was conquered', ['1453']),
        ('What is the capital of Turkey', ['Ankara']),
        ('What is the largest city of Turkey', ['Istanbul']),
        ('What is the name of the world\'s best university', ['Harvard', 'Peking University']),
        ('What is the name of the world\'s longest river', ['Nile', 'Amazon']),
        ('What is the brand of the world\'s most expensive car', ['Rolls-Royce']),
        ('What is the bloodiest war in human history', ['World War II', 'World War I']),
        ('What is the name of the best seller book', ['Real Marriage', '\'Real Marriage\' on']),
        ('What is the lowest point in the ocean', ['the Mariana Trench']),
        ('Who invented General Relativity', ['Einstein']),
        ('When was United Nations formed', ['1945'])
    ]

    omniscient = Omniscient(spacy.load('en'))
    best_score = 0
    best_coefficient = None
    i = 0
    while True:
        i += 1
        print('Iteration: ' + str(i))
        score = 0
        omniscient.randomize_coefficient()
        print(omniscient.coefficient)

        for (question, answers) in dataset:
            if omniscient.respond(question) in answers: score += 1
        
        if score >= best_score:
            print('\n--- !!! NEW BEST !!! ---')
            best_score = score
            best_coefficient = omniscient.coefficient
            print(str(best_score) + '/' + len(dataset))
            print(best_coefficient)
            print('------------------------\n')
