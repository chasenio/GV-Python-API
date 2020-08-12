#!/usr/bin/env python
# -* coding: utf-8 -*
# create by cvno on 2018/11/4 12:54
import os
import json
import time
from flask import Flask
from threading import Timer
from datetime import datetime
from gvapi import Voice


app = Flask(__name__)


voice = Voice(os.environ.get('GV_USR'),os.environ.get('GV_PWD'))
to_number = os.environ.get('TO_NUMBER')

while not voice.status['init']: # wait...
    time.sleep(3)
    continue

@app.route('/sms/<int:number>/<content>', methods=['GET', 'POST'])
def sms(number, content):
    # 发送 sms
    res = voice.send_sms(number, content)
    data = {'number': number,'content': content, 'res': res}
    return json.dumps(data, ensure_ascii=False)


class Scheduler(object):
    # loop
    def __init__(self, sleep_time, function):
        self.sleep_time = sleep_time
        self.function = function
        self._t = None

    def start(self):
        if self._t is None:
            self._t = Timer(self.sleep_time, self._run)
            self._t.start()
        else:
            raise Exception("this timer is already running")

    def _run(self):
        self.function()
        self._t = Timer(self.sleep_time, self._run)
        self._t.start()

    def stop(self):
        if self._t is not None:
            self._t.cancel()
            self._t = None


def task():
    voice.send_sms(to_number,'{}'.format(datetime.now().strftime("%Y年%m月%d日, %H时%M分%S秒, 星期%w")))


if __name__ == '__main__':
    try:
        # start loop
        scheduler = Scheduler(604800, task)  # 每隔一周发送一次
        scheduler.start()
        ENV_API = os.environ.get('GVAPI_IS_DEV')
        if ENV_API and json.loads(ENV_API):     # dev run
            app.run(host='0.0.0.0', debug=False)
            exit(0)
        app.run()
    except KeyboardInterrupt as e:
        print('Bye.')
