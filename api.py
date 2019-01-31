#!/usr/bin/python3
# -*- coding: utf-8 -*-


import datetime
import time
import os
from pprint import pprint

from sqlalchemy import create_engine

from config import Config
from utilities import tts_kill


def get_notification(engine, user='Eff'):
    connect = engine.connect()
    query = "SELECT drug, quantity, before_meal FROM `in-home-nursing`.medicine WHERE id = '{}' and {} = 1"
    drugs = {}
    when = ''
    msg = ''
    # while True:
    if datetime.datetime.now().hour in [9, 10]:
        when = 'morning'
    if datetime.datetime.now().hour in [13, 14]:
        when = 'afternoon'
    if datetime.datetime.now().hour in [17, 20]:
        when = 'evening'
    if when != '':
        results = connect.execute(query.format(user, when))
        for result in results.fetchall():
            drugs[result[0]] = {'Quantity': int(result[1]), 'Before': bool(result[2])}
        # print(drugs)
        for key, value in sorted(drugs.items(), key=lambda k_v: k_v[1]['Before'], reverse=True):
            msg = msg + f"{value['Quantity']} {key}"
    print(msg)
    # pprint(drugs)
    # tts_kill()
    # userin.say()
    # print()
        # else:
        #     time.sleep(60)


if __name__ == '__main__':
    engine = create_engine('mysql+pymysql://' + Config.MYSQL_USER + ':' + Config.MYSQL_PASS + '@' + Config.MYSQL_HOST + '/' + Config.MYSQL_DB)
    get_notification(engine)
