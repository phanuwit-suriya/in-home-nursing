import argparse
import datetime
import inspect
import os
import re
import subprocess
import sys
import time
import uuid
from multiprocessing import Process
from os.path import expanduser
from random import choice
from threading import Thread, Timer

import pyowm
import pytz
import requests.exceptions
import spacy
import wikipedia
import wikipedia.exceptions
import youtube_dl
from geopy.geocoders import Nominatim
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from timezonefinder import TimezoneFinder
from tinydb import Query, TinyDB

from api import get_notification
from arithmetic import arithmetic_parse
from config import Config
from coref import NeuralCoref
from database import Base
from DeepQA import DeepQA
from learn import Learner
from nlplib import Classifier, Helper
from omniscient import Omniscient
from utilities import TextToAction, nostderr, nostdout, tts_kill

PATH = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
FNULL = open(os.devnull, 'w')
GENDER_PREFIX = {'male': 'Sir', 'female': 'My Lady'}
CONVERSATION_ID = uuid.uuid4()

userin = None
nlp = spacy.load('en')
learner = Learner(nlp)
omniscient = Omniscient(nlp)
qa = DeepQA()
coref = NeuralCoref()

try:
    raw_input
except NameError:
    raw_input = input


class VirtualAssistant:
    class ResumableTimer:
        def __init__(self, timeout, userin):
            self.timeout = timeout
            self.userin = userin
            self.is_pause = False
            self.start()

        def start(self):
            self.timer = Timer(self.timeout, self.userin.say, ['Timeout'])
            self.timer.start()
            self.start_time = time.time()

        def pause(self):
            self.is_pause = True
            self.pause_time = time.time()
            self.timer.cancel()

        def resume(self):
            self.is_pause = False
            self.timer = Timer(self.timeout - (self.pause_time - self.start_time), self.userin.say, ['Timeout'])
            self.timer.start()

        def cancel(self):
            self.timer.cancel()

        def remain(self):
            remaining_time = self.timeout - (self.pause_time - self.start_time) if self.is_pause else self.timeout - (time.time() - self.start_time)
            timeleft = {'hour': 0, 'minute': 0, 'second': 0}
            timeleft['hour'] = int(remaining_time // 3600)
            timeleft['minute'] = int((remaining_time % 3600) // 60)
            timeleft['second'] = int((remaining_time % 3600) % 60)
            return f"Your timer has {str(timeleft['hour']) + ' hour ' if timeleft['hour'] != 0 else ''}" \
                   f"{str(timeleft['minute']) + ' minute ' if timeleft['minute'] != 0 else ''}" \
                   f"{str(timeleft['second']) + ' second ' if timeleft['second'] != 0 else ''} left"

    def __init__(self, args, userin, user_full_name='John Doe', user_prefix='sir'):
        self.args = args
        self.userin = userin
        self.user_full_name = user_full_name
        self.user_prefix = user_prefix
        self.active = False
        self.set_timer = False
        
        home = expanduser('~')
        # self.config_file = TinyDB(home + '/.config.json')
        self.config_file = TinyDB(os.path.join(home, ".config.json"))

    def command(self, com):
        args = self.args
        userin = self.userin
        user_full_name = self.user_full_name
        user_prefix = self.user_prefix
        config_file = self.config_file

        if isinstance(com, str) and com:
            com = com.strip()
        else:
            return False

        print(f'You: {com.upper()}')

        doc = nlp(com.upper())
        h = Helper(doc)

        if self.active and (h.check_verb_lemma('wake') and h.check_nth_lemma(-1, 'up')):
            return userin.say('')
        if not self.active and (h.check_verb_lemma('wake') and h.check_nth_lemma(-1, 'up')):
            self.active = True
            return userin.say(choice([
                f"Yes, {user_prefix}.",
                f"{user_prefix}, tell me your wish.",
                "Yes, I'm waiting.",
                "What is your order?",
                "Ready for the order."]))
        if self.active and ((h.check_verb_lemma('go') and h.check_noun_lemma('sleep')) or (h.check_verb_lemma('stop') and h.check_verb_lemma('listen'))):
            self.active = False
            return userin.say("I'm going to sleep")
        if h.directly_equal(['enough']) or (h.check_verb_lemma('shut') and h.check_nth_lemma(-1, 'up')):
            self.active = False
            tts_kill()
            return userin.say(f"Sorry, {user_prefix}.")
        if (h.check_wh_lemma('what') and h.check_deps_contain('your name')) or (h.check_wh_lemma('who') and h.check_text('you')):
            return userin.say(f"My name is Jon Snow, {user_prefix}.")
        if h.check_wh_lemma('what') and h.check_deps_contain('gender'):
            return userin.say(f"I have a female voice but I don't have gender identity. I'm a computer program, {user_prefix}.")
        if (h.check_wh_lemma('who') and h.check_text('I')) or (h.check_verb_lemma('say') and h.check_text('my') and h.check_lemma('name')):
            return userin.say(f"Your name is {user_full_name}, {user_prefix}.")

        if h.check_lemma('set') and h.check_noun_lemma('timer'):
            timeout = h.get_time()
            self.timer = self.ResumableTimer(timeout['hour'] * 3600 + timeout['minute'] * 60 + timeout['second'], userin)
            return userin.say(f"OK, Set timer for {str(timeout['hour']) + ' hour ' if timeout['hour'] != 0 else ''}" \
                              f"{str(timeout['minute']) + ' minute ' if timeout['minute'] != 0 else ''}" \
                              f"{str(timeout['second']) + ' second ' if timeout['second'] != 0 else ''}")
        try:
            if h.check_deps_contain('how much time left'):
                return userin.say(self.timer.remain())
            if h.check_verb_lemma('pause') and h.check_noun_lemma('timer'):
                self.timer.pause()
                return userin.say('Pause your timer')
            if (h.check_verb_lemma('resume') or h.check_verb_lemma('restart')) and h.check_noun_lemma('timer'):
                self.timer.resume()
                return userin.say('Resume your timer')
            if h.check_verb_lemma('cancel') and h.check_noun_lemma('timer'):
                self.timer.cancel()
                return userin.say('Already cancel your timer')
        except AttributeError:
            return userin.say("Have not set a timer yet.")
        
        if h.check_lemma('be') and h.check_lemma('-PRON-') and (h.check_lemma('lady') or h.check_lemma('woman') or h.check_lemma('girl')):
            config_file.update({'gender': 'female'}, Query().datatype == 'gender')
            config_file.remove(Query().datatype == 'callme')
            self.user_prefix = 'my lady'
            return userin.say('Pardon, ' + self.user_prefix + '.')
        if h.check_lemma('be') and h.check_lemma('-PRON-') and (h.check_lemma('sir') or h.check_lemma('man') or h.check_lemma('boy')):
            config_file.update({'gender': 'male'}, Query().datatype == 'gender')
            config_file.remove(Query().datatype == 'callme')
            self.user_prefix = 'sir'
            return userin.say('Pardon, ' + self.user_prefix + '.')
        if h.check_lemma('call') and h.check_lemma('-PRON-'):
            title = ''
            for token in doc:
                if token.pos_ == 'NOUN':
                    title += ' ' + token.text
            title = title.strip()
            if not args['server']:
                callme_config = config_file.search(Query().datatype == 'callme')
                if callme_config:
                    config_file.update({'title': title}, Query().datatype == 'callme')
                else:
                    config_file.insert({'datatype': 'callme', 'title': title})
            self.user_full_name = title
            return userin.say('OK, ' + self.user_full_name + '.')

        if h.check_wh_lemma('what') and h.check_noun_lemma('temperature'):
            city = 'Bangkok'
            for ent in doc.ents:
                if ent.label_ == 'GPE':
                    city = ent.text
            city = city.strip()
            if city:
                owm = pyowm.OWM('16d66c84e82424f0f8e62c3e3b27b574')
                reg = owm.city_id_registry()
                try:
                    weather = owm.weather_at_id(reg.ids_for(city)[0][0]).get_weather()
                    return userin.say(f"The temperature in {city} is {weather.get_temperature('celsius')['temp']} degree celsius.")
                except IndexError:
                    return userin.say(f"Sorry, {user_prefix}. But I couldn't find a city named {city} on the internet.")
        
        if h.check_wh_lemma('what') and h.check_noun_lemma('time'):
            location = 'Thailand'
            for ent in doc.ents:
                if ent.label_ == 'GPE':
                    location = ent.text
            location = location.strip()
            if location:
                gl = Nominatim(user_agent='In-home nursing')
                tf = TimezoneFinder()
                try:
                    loc = gl.geocode(location)
                    lng, lat = loc.longitude, loc.latitude
                    tz = tf.timezone_at(lng=lng, lat=lat)
                    now = datetime.datetime.now(pytz.timezone(tz)) 
                    return userin.say(choice([
                        f"The time in {location} is {now.hour} {now.minute}.",
                        f"It is {now.hour} {now.minute} in {location}"]))
                except (pytz.exceptions.AmbiguousTimeError, AttributeError):
                    return userin.say(f"Sorry, {user_prefix}. But I couldn't find a location named {location} on my library.")
        
        com_ = com
        com = coref.resolve(com)
        artithmetic_response = arithmetic_parse(com_)
        if artithmetic_response:
            return userin.say(artithmetic_response)
        else:
            learner_response = learner.response(com)
            if learner_response:
                return userin.say(learner_response)
            else:
                omniscient_response = omniscient.respond(com, not args['silent'], userin, user_prefix, args['server'])
                if omniscient_response:
                    return userin.say(omniscient_response)
                else:
                    qa_response = qa.respond(com_, user_prefix)
                    if qa_response:
                        return userin.say(qa_response)


def start(args, userin):
    engine = create_engine('mysql+pymysql://' + Config.MYSQL_USER + ':' + Config.MYSQL_PASS + '@' + Config.MYSQL_HOST + '/' + Config.MYSQL_DB)
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    db_session = DBSession()
    learner.db_session = db_session

    notification = Thread(target=get_notification, args=(engine, userin, user, ))
    notification.start()

    va = VirtualAssistant(args, userin, user_full_name, user_prefix)
    if args['cli']:
        while True:
            sys.stdin.flush()
            sys.stdout.flush()

            com = raw_input('Enter your command: ')
            T = Thread(target=(va.command), args=(com,))
            T.start()
            T.join()
    elif args['gspeech']:
        from stt import GoogleSpeechRecognizer

        recognizer = GoogleSpeechRecognizer()
        recognizer.recognize(va)
    else:
        raise Exception('Choose')


def greet(userin):
    global user_full_name
    global user_prefix
    global config_file

    user_full_name = os.popen("getent passwd $LOGNAME | cut -d: -f5 | cut -d, -f1")
    user_full_name = user_full_name[:-1]
    home = expanduser('~')
    config_file = TinyDB(os.path.join(home, ".config.json"))
    callme_config = config_file.search(Query().datatype == 'callme')
    if callme_config:
        user_prefix = callme_config[0]['title']
    else:
        gender_config = config_file.search(Query().datatype == 'gender')
        if gender_config:
            user_prefix = GENDER_PREFIX[gender_config[0]['gender']]
        else:
            gender = Classifier.gender(user_full_name.split(' ', 1)[0])
            config_file.insert({'datatype': 'gender', 'gender': gender})
            user_prefix = GENDER_PREFIX[gender]


def initiate():
    """
    The top-level method to serve as the entry point of Jon Snow.

    This method parses the command-line arguments and handles the top-level initiations accordingly.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument('-c', '--cli',
                    help="Command-line interface mode. Give commands to Jon Snow via command-line inputs " \
                         "(keyboard) instead of audio inputs (microphone).", action='store_true')
    ap.add_argument('g', '--gspeech',
                    help="Use Google Speech Recognition service", action='store_true')
    args = vars(ap.parse_args())

    try:
        global qa
        userin = TextToAction(args)
        # greet(userin)
        start(args, userin)
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == '__main__':
    initiate()
