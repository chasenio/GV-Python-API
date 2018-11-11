#!/usr/bin/env python
# -* coding: utf-8 -*
# create by git@cvno on 2018/1/2 10:23
import re
import ssl
import time
import json
import logging
import traceback
import urllib3
import requests
import threading
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ERROR
from selenium.common.exceptions import *
from requests.exceptions import *

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

# 禁用 HTTPS SSL 安全警告
from urllib3.exceptions import InsecureRequestWarning

urllib3.disable_warnings(InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context  # 忽略 ssl 证书


class Singleton(object):
    '''基类 单例模式'''

    def __new__(cls, *args, **kwargs):
        ''' not obj -> create obj, else return obj'''
        if not hasattr(cls, "_instance"):
            cls._instance = super(Singleton, cls).__new__(cls)
        return cls._instance


def init(func):
    'yield next(0) 协程初始化'

    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        next(res)
        return res

    return wrapper


class NotOpenGoogle(Exception):
    '''打不开谷歌'''
    pass


class ProxyError(Exception):
    '''没有使用代理'''
    pass


class Voice(Singleton):
    '''google voice send info'''
    check_msg_url = {}
    status = {'self': None, # self : 程序自身是否正常
              'login': False, # login: 登录状态
              'init': False, # init: 数据初始化是否完成
              'guard': False, # guard: 是否启动触发过登录状态维护
              'check': False, # check: check参数是否获取成功
              'auto': False # auto: 是否开启自动回复
              }  # 0: deviant, 1: normal , 2: error

    __login_url = 'https://accounts.google.com/ServiceLogin?service=grandcentral&passive=1209600&continue=https://www.google.com/voice/b/0/redirection/voice&followup=https://www.google.com/voice/b/0/redirection/voice#inbox'
    __user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36'
    __window_size_width = 1024
    __window_size_height = 768
    __page_load_timeout = 20
    __time_out = 30
    __cookie = {}
    __intervals = 3
    __driver = None
    _gc_data = None
    __try_time = 2
    _match = {}

    def __init__(self, email, passwd, debug=True):
        self.__email = email
        self.__passwd = passwd
        self.debug = debug
        self._gc_data_name = '_gcData'
        self.__browser_name = 'PhantomJS'  # 默认
        self.__module = 'selenium.webdriver'

        self.log = self.__voice_log()
        if not (email and passwd):
            raise TypeError('email or passwd is empty!')

        t = threading.Thread(target=self.start, name='Analog logon')    # 启动登录线程
        t.setDaemon(True)
        t.start()

    def __guard(self):
        ''' 守护线程, 如果当前登录的帐号发生异常则重新启动登录流程'''
        while self.status['login'] and not self.status['guard']:
            time.sleep(2)
            continue
        self.status['guard'] = True
        e = self.__login()
        e.send(None)

    def start(self):
        '''程序启动'''
        if self.status['login']:
            pass
        self.log.send(('start...',))
        self._initial()  # 钩子
        e = self.__login()
        e.send(None)

    @init
    def __login(self):
        '''
        login Google
        :return: data -> dict
        '''
        while True:
            yield
            if self.status['login']:
                pass
            self.log.send(('ready...',))
            if self.__driver:
                self.log.send(('login again...',))
                self.__driver.quit()
                continue
            self.__driver = self.__browser()
            try:
                self.__driver.get(self.__login_url)
                # send email
                self.log.send(('enter email...',))
                self.__driver.find_element_by_xpath('//*[@id="identifierId"]').send_keys(self.__email)  # inp email
                # self.screenshots(self.__driver)  # debug -> img -> title -> time

                # js -> next
                click_js_str = 'document.getElementById("identifierNext").click();'
                self.__driver.execute_script(click_js_str)  # run js -> user page -> passwd page
                # self.screenshots(self.__driver)  # debug -> img -> title -> time

                # Wait password input box ...
                WebDriverWait(self.__driver, self.__time_out, self.__intervals).until(
                    EC.visibility_of_element_located((By.XPATH, '//*[@id="password"]')))
                # send password
                self.log.send(('enter password...',))
                self.__driver.find_element_by_xpath('//*[@id="password"]/div[1]/div/div[1]/input').send_keys(self.__passwd)

                # js -> next
                click_js_str = 'document.getElementById("passwordNext").click();'
                self.__driver.execute_script(click_js_str)  # run -> js | next  -> login

                # Wait page user phoneNumber
                WebDriverWait(self.__driver, self.__time_out, self.__intervals).until(
                    EC.presence_of_element_located((By.ID, 'gc-iframecontainer')))
                self.log.send(('login successful...',))
                # self.screenshots(self.__driver)  # debug -> img -> title -> time

                self.status['login'] = True  # login successful flag
                e = self.__initial()
                e.send(None)
            except TimeoutException as e:   # 如果出现超时,就重试
                time.sleep(1)
                e = self.__login()
                e.send(None)
            except NotOpenGoogle as e:  # 打不开谷歌
                raise NotOpenGoogle('Can not open google, pleasw use VPN, you know...')
            except Exception as e:
                self.screenshots(self.__driver)  # debug -> img -> title -> time
                self.status['self'] = 0
                self.__debug(e)

    @init
    def __voice_log(self, level=0):
        '''
        logging 程序运行日志
        :param msg: ﻿message
        :param level: log level (0,info) (1,warning) (2,error)
        '''
        logger = logging.getLogger()
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        fh = logging.FileHandler('run.log')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        logger.level = logging.INFO
        if self.debug:  # to screen
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            logger.addHandler(ch)   # 输出到屏幕
        while True:
            log = yield
            if len(log) > 1:
                level, msg = log
            if level == 0:  # info
                logger.info(log[0])
            if level == 1:  # warning
                logger.warning(msg)
            elif level == 2:# error
                logger.error(msg)
            else:
                pass

    def _initial(self):
        ''' 钩子, 自定义一些配置的操作 '''
        pass

    @init
    def __initial(self):
        ''' initial data 初始化数据 '''
        # get javascript value  -> _gcData
        while True:
            yield
            if self.status['login']:
                self.log.send(('initialization data...',))
                self._gc_data = self.__driver.execute_script('return %s' % self._gc_data_name)
                if self._gc_data is None:  # 如果获取不到这个参数就回去重新获取 直到获取到为止
                    time.sleep(self.__try_time)
                    continue
                # format url
                self.__cookie_func(self.__driver.get_cookies())  # process cookie 处理 cookie
                self._send_msg_url = '{}/sms/send/'.format(self._gc_data['baseUrl'])  # process send msg url
                self.__call_url = '{}/call/connect/'.format(self._gc_data['baseUrl'])  # 拨打电话的请求地址
                self.__call_cancel_url = '{}/call/cancel/'.format(self._gc_data['baseUrl'])  # 取消拨打电话的请求地址
                self.__mark_url = '{}/inbox/mark/'.format(self._gc_data['baseUrl'])  # 标记为已读的请求地址
                self.__del_msg_url = '{}/inbox/deleteMessages/'.format(self._gc_data['baseUrl'])  # 删除信息
                self.__star_url = '{}/inbox/star/'.format(self._gc_data['baseUrl'])  # 收藏信息
                self.__dow_msg_url = '{}/inbox/recent/'.format(self._gc_data['baseUrl'])  # 下载信息
                self.__quick_add_url = '{}//phonebook/quickAdd/'.format(self._gc_data['baseUrl'])
                self.__voicemail_ogg_str = '{0}/media/send_voicemail_ogg/{1}?read=0'

                if len(self._gc_data['phones']) > 1:  # 获取绑定的号码
                    for k, v in self._gc_data['phones'].items():
                        if self._gc_data['phones'][k]['name'] != 'Google Talk':
                            self.__call_phone_for = self._gc_data['phones'][k]
                            break
                            # 是否需要检测新消息
                self.driver.quit()
                self.status['init'] = True  # 初始化完成
                # 开启守护线程
                t = threading.Thread(target=self.__guard, name='Guard')
                t.setDaemon(True)
                t.start()

                self.__check_msg_par()  # TODO OFF check msg  # 去获取检测新消息的参数, 如果不需要这项功能可以取消掉

            else:
                self.log.send(('not login', 1))

    def __cookie_func(self, cookie_list):
        '''处理 cookie '''
        self.log.send(('process cookie...',))
        try:
            for i in cookie_list:
                self.__cookie[i['name']] = i['value']
            return self.__cookie
        except Exception as e:
            self.__debug(e)

    def __check_msg_par(self):
        ''' get checkMessages token (must) 获取检测消息时url的必须参数'''
        self.log.send(('get checkMessages token...',))

        data = {'xpc': {'tp': None, 'osh': None, 'pru': 'https://www.google.com/voice/xpc/relay',
                        'ppu': 'https://www.google.com/voice/xpc/blank/',
                        'lpu': '{}/voice/xpc/blank/'.format(self._gc_data['xpcUrl'])}}

        url = '{}/voice/xpc/'.format(self._gc_data['xpcUrl'])
        r = self._requests(url, params=data)
        par = re.findall("\'(.*?)\'", r.text)[0]
        self.log.send(('xpc: %s' % par,))

        # https://clientsx.google.com/voice/xpc/checkMessages?r=xxxxxxx
        self.check_msg_url['url'] = '{0}/voice/xpc/checkMessages'.format(self._gc_data['xpcUrl'])
        self.check_msg_url['par'] = {'r': par}
        self.status['check'] = True

        # 开启检测消息线程
        if self.status['auto']:
            t = threading.Thread(target=self._check_sms, args=(self.reply_sms,), name='check-new-sms')
            t.setDaemon(True)
            t.start()

    def __debug(self, e):
        self.status['self'] = 0  # 把当前程序状态改为异常
        if self.debug:
            self.screenshots(self.driver)  # 保存当前浏览器截图
            self.log.send((2, traceback.format_exc()))

    def set_agent(self, agent):
        '''浏览器请求头'''
        self.__user_agent = agent

    @property
    def current_url(self):
        ''' 模拟浏览器当前的url '''
        try:
            return self.driver.current_url
        except Exception:
            pass

    @property
    def __headers(self):
        '''send post headers 请求头'''
        return {'host': 'www.google.com', 'user-agent': self.__user_agent,
                'referer': self._gc_data['baseUrl'], 'content-type': 'application/x-www-form-urlencoded;charset=UTF-8'}

    def _requests(self, url, params=None, data=None, method='get'):
        '''
        requests uniform, code reuse  封装请求方法
        :param url: request url 请求的地址
        :param method: request method get/post
        :param params: request get params get 请求的参数
        :param data: request post data post 请求的参数
        :return: Response对象
        '''
        try:
            if method == 'get':
                r = requests.get(url, params=params, headers=self.__headers, cookies=self.__cookie, verify=False)
                return r
            elif method == 'post':
                r = requests.post(url, data=data, headers=self.__headers, cookies=self.__cookie, verify=False)
                return r
            else:  # not support method #TODO img? 发送图片
                pass
        except AttributeError as e:
            return None
        except OSError as e:  # 如果是本地测试出现这个报错要更换为全局代理
            raise ProxyError('please proxy global')
        except Exception as e:
            self.__debug(e)

    def check_unread_msg(self):
        '''
        Get all of the unread SMS messages in a Google Voice inbox.
        检测有没有新消息
        :return dict
        '''
        if self.status['login'] and self.status['check']:
            r = self._requests(self.check_msg_url['url'], params=self.check_msg_url['par'])  # check...
            ret = r.json()
            return ret
        self.log.send((1, 'check msg not ready'))

    def _check_sms(self, func):
        '''检测未读 sms, 并做出自定义的操作'''
        while self.status['login'] and self.status['check']:
            res = self.check_unread_msg()  # check sms...
            if res['data']['unreadCounts']['sms'] > 0:  # have ...
                sms_list = self.unsms
                for i in sms_list:
                    if i['text'].strip().upper() in self._match:    # 匹配关键字
                        t = threading.Thread(target=func, args=(i,), name='reply sms')
                        t.setDaemon(True)
                        t.start()
            else:
                time.sleep(10)
        self.log.send((1, 'check sms not ready'))

    def reply_sms(self, data):
        '''
        回复这条 sms
        :param data: 需要回复的 sms 的数据
        '''
        self.log.send(('ready reply sms',))
        r = self.send_sms(data['number'], self._match[data['text']])
        if r['ok']:
            self.log.send(('[success] reply sms to: %s' % data['number'],))
        else:
            self.log.send((1, '[miss] reply sms to: %s' % data['number']))

    def __process_xml(self, r):
        '''
        处理 xml ,并转化为 BeautifulSoup 对象
        :param r: Response
        :param type: (sms 1) / (voicemail 0)
        :param read_type: (0 unread) / (1 read)
        :return  type dict
        '''
        data = {}
        if self.status['login']:
            tree = ET.fromstring(r.content)
            for elem in tree.iter():
                if elem.tag == 'json':
                    data['json'] = json.loads(elem.text)
                    continue
                if elem.tag == 'html':
                    data['html'] = elem.text
            self.log.send(('process new msg...',))
            data['soup'] = BeautifulSoup(data['html'], 'html.parser')

            return data

    @property
    def unsms(self):
        '''
        获取未读的 sms
        :return: dict
        '''
        par = {'v': self._gc_data['v']}  # token
        if self.status['login']:
            sms_list = []
            r = self._requests(self.__dow_msg_url, params=par)
            data = self.__process_xml(r)
            msg_list = data['soup'].find_all(name='div', class_='gc-message-unread')  # 所有的未读短信消息
            # data = {'sms': [], 'voicemail': []}
            for msg in msg_list:
                attr = msg.get('class')
                if 'gc-message-sms' in attr:  # sms
                    sms = {}
                    sms['id'] = msg['id']
                    sms['number'] = msg.find(name='span', class_='gc-message-sms-from').text.strip()[:-1]  # 去掉空格并切掉最后的冒号
                    # -----  处理时间  -----
                    time_str = msg.find(name='span', class_='gc-message-sms-time').text.strip()
                    local_time = time.strftime("%Y-%m-%d", time.localtime())
                    sms_time_str = ''.join((local_time, ' ', time_str))
                    sms_time = time.strptime(sms_time_str, '%Y-%m-%d %I:%M %p')
                    sms['time'] = time.strftime("%Y-%m-%d %X", sms_time)
                    sms['text'] = msg.find(name='span', class_='gc-message-sms-text').text
                    self.log.send(('[sms] time: {0}; id:{1} .'.format(sms['time'], sms['id']),))
                    print(sms)
                    sms_list.append(sms)
            return sms_list

    @property
    def read_sms(self):
        '''
        所有的已读读短信消息
        :return: dict
        '''
        par = {'v': self._gc_data['v']}  # token
        if self.status['login']:
            sms_list = []
            r = self._requests(self.__dow_msg_url, params=par)
            data = self.__process_xml(r)
            msg_list = data['soup'].select('div.gc-message-sms.gc-message-read')  # 所有的已读读短信消息
            # data = {'sms': [], 'voicemail': []}
            for msg in msg_list:
                attr = msg.get('class')
                if 'gc-message-sms' in attr:  # sms
                    sms = {}
                    sms['id'] = msg['id']
                    sms['number'] = msg.find(name='span', class_='gc-message-sms-from').text.strip()[:-1]  # 去掉空格并切掉最后的冒号
                    sms['text'] = msg.find(name='span', class_='gc-message-sms-text').text
                    sms['time'] = msg.find(name='span', class_='gc-message-sms-time').text.strip()
                    sms_list.append(sms)
            return sms_list

    @property
    def voicemail(self):
        '''
        获取未读的 voicemail, 包括文本和语音(下载url 地址)
        :return:
        '''
        par = {'v': self._gc_data['v']}  # token
        if self.status['login']:
            voice_list = []
            r = self._requests(self.__dow_msg_url, params=par)
            data = self.__process_xml(r)
            msg_list = data['soup'].find_all(name='div', class_='gc-message-unread')  # 所有的未读语音消息
            for msg in msg_list:
                attr = msg.get('class')
                if 'gc-message-sms' in attr:
                    continue
                voicemail = {}
                voicemail['id'] = msg['id']
                voicemail['number'] = msg.find(name='span', class_='gc-nobold').text
                voicemail['time'] = msg.find(name='span', class_='gc-message-time').text
                voicemail['text'] = msg.find(name='span', class_='gc-edited-trans-text').text
                voicemail['ogg_url'] = self.__voicemail_ogg_str.format(self._gc_data['baseUrl'], voicemail['id'])

                if len(voicemail['text']) < 1:
                    voicemail['text'] = '[None] - please go to the website...'
                voice_list.append(voicemail)
                self.log.send(('[voicemail] time: {0}; id:{1} .'.format(voicemail['time'], voicemail['id']),))
            return voice_list

    def dow_voicemail(self, url):
        '''
        下载 voicemail 的音频
        :param url: voicemail 下载地址的url
        :return: r.content   二进制数据
        '''
        r = self._requests(url)
        return r.content

    def quick_add(self, name, number, phone_type=0):
        '''
        添加到 google phonebook
        :param name: 名字  备注
        :param number: 10 位合法的美国手机号码
        :param phone_type: 类型 : {0:'MOBILE',1:'WORK',2:'HOME'}
        :return:
        '''
        phone_type_dict = {0: 'MOBILE', 1: 'WORK', 2: 'HOME'}
        if self.status['login']:
            data = {'phoneNumber': '+1%s' % number,
                    'phoneType': phone_type_dict[phone_type],
                    '_rnr_se': self._gc_data['_rnr_se'],
                    'needsCheck': 1}
            r = self._requests(self.__quick_add_url, data=data, method='post')
            ret = r.json()
            if ret['ok']:
                return ret
            else:
                self.log.send((1, 'abnormal status, log in again'))
                self.status['login'] = False  # 状态异常
        return

    def mark(self, msg_id, read=1):
        '''
         把信息标记为已读
        :param msg_id: msg 的唯一 id 它必须是存在的
        :param read: (0,未读) (1,已读)
        :return:
        '''
        if self.status['login']:
            data = {'_rnr_se': self._gc_data['_rnr_se'], 'messages': msg_id, 'read': read}
            r = self._requests(self.__mark_url, data=data, method='post')
            ret = r.json()
            if ret['ok']:
                return ret
            else:
                self.log.send((1, 'abnormal status, log in again'))
                self.status['login'] = False  # 状态异常
        return

    def star(self, msg_id):
        ''' 把信息标记为收藏 '''
        if self.status['login']:
            data = {'_rnr_se': self._gc_data['_rnr_se'], 'messages': msg_id, 'star': 1}
            r = self._requests(self.__star_url, data=data, method='post')
            ret = r.json()
            if ret['ok']:
                return ret
            else:
                self.log.send((1, 'abnormal status, log in again'))
                self.status['login'] = False  # 状态异常
        return

    def unstar(self, msg_id):
        ''' 把已经标记收藏的消息取消收藏标记 '''
        if self.status['login']:
            data = {'_rnr_se': self._gc_data['_rnr_se'], 'messages': msg_id, 'star': 0}
            r = self._requests(self.__star_url, data=data, method='post')
            ret = r.json()
            if ret['ok']:
                return ret
            else:
                self.log.send((1, 'abnormal status, log in again'))
                self.status['login'] = False  # 状态异常
        return

    def del_msg(self, msg_id):
        ''' 删除信息 '''
        if self.status['login']:
            data = {'_rnr_se': self._gc_data['_rnr_se'], 'messages': msg_id, 'trash': 1}
            r = self._requests(self.__del_msg_url, data=data, method='post')
            ret = r.json()
            if ret['ok']:
                return ret
            else:
                self.log.send((1, 'abnormal status, log in again'))
                self.status['login'] = False  # 状态异常
        return

    def missed(self):
        '''错过的来电'''
        pass

    def send_sms(self, number, text):
        '''
        给指定的美国号码发送文本消息
        :param number: 符合格式美国号码 +1XXXXXXXXXX
        :param text: 要发送的消息
        :return: post 结果, 消息是否发送成功
        '''
        if self.status['login']:
            # 数据格式
            msg = {'id': None, 'phoneNumber': number, 'text': text, 'sendErrorSms': 0,
                   '_rnr_se': self._gc_data['_rnr_se']}
            r = self._requests(self._send_msg_url, method='post', data=msg)  # post sms
            ret = r.json()
            if ret['ok']:
                return ret
            else:
                self.log.send((1, 'abnormal status, log in again'))
                self.status['login'] = False  # 状态异常
        return

    def call(self, number):
        '''
        拨打电话到指定美国号码
        :param number: 符合格式美国号码 +1XXXXXXXXXX
        :return: post 请求的结果, 拨打状态, 以及此次通信的 callId
        '''
        if self.status['login']:
            # 数据格式
            data = {'outgoingNumber': number, 'remember': 0, 'phoneType': self.__call_phone_for['type'],
                    'subscriberNumber': self._gc_data['number']['raw'],
                    'forwardingNumber': self.__call_phone_for['phoneNumber'],
                    '_rnr_se': self._gc_data['_rnr_se']}

            r = self._requests(self.__call_url, data=data, method='post')  # 拨打
            ret = r.json()
            if ret['ok']:
                return ret
            else:
                self.log.send((1, 'abnormal status, log in again'))
                self.status['login'] = False  # 状态异常
        return

    def cancel_call(self, call_id):
        '''
        取消拨打
        :param call_id: call 方法返回的 callId,
        :return: 请求的结果, 取消通话是否成功
        '''
        if self.status['login']:
            # 数据格式
            data = {'outgoingNumber': None,
                    'forwardingNumber': None,
                    'cancelType': 'C2C',
                    '_rnr_se': self._gc_data['_rnr_se'],
                    'callId': call_id}
            r = self._requests(self.__call_cancel_url, data=data, method='post')
            return r.json()  # {"ok" : false}
        return

    def set_time_out(self, sec):
        '''
        set page load time out
        :param sec: type int
        '''
        self.__page_load_timeout = int(sec)

    def set_browser(self, browser_name):
        ''' PhantomJS / Chrome / Firefox '''
        self.__browser_name = browser_name

    def set_login_url(self, url):
        '''set login url 如果你需要改变登录的地址 '''
        self.__login_url = url

    def set_intervals(self, sec):
        '''set get html tag intervals time 设置寻找网页标签的间隔时间'''
        self.__intervals = sec

    def set_match(self, data):
        '''设置匹配关键字,字典格式'''
        self._match = data

    def __createInstance(self, module_name, class_name, *args, **kwargs):
        '''
        create user input browser object 动态导入浏览器浏览器类型模块
        :return: object
        '''

        headers = {'Accept': '*/*',
                   'Accept-Encoding': 'gzip, deflate, sdch',
                   'Accept-Language': 'en-US,en;q=0.8',
                   'Cache-Control': 'max-age=0',
                   'User-Agent': self.__user_agent,
                   }
        # set browser header
        for key, value in headers.items():
            webdriver.DesiredCapabilities.PHANTOMJS['phantomjs.page.customHeaders.{}'.format(key)] = value
        module_meta = __import__(module_name, globals(), locals(), [class_name])
        try:
            class_meta = getattr(module_meta, class_name)
            obj = class_meta(*args, **kwargs)
        except AttributeError as e:
            raise AttributeError('not is %s' % self.__browser_name)
        return obj

    def __browser(self):
        '''
        browser obj , browser header 创建要模拟的浏览器
        :return obj
        '''
        from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

        dcap = dict(DesiredCapabilities.PHANTOMJS)
        dcap["phantomjs.page.settings.userAgent"] = (self.__user_agent)  # 设置 userAgent

        driver = self.__createInstance(self.__module, self.__browser_name,
                                       desired_capabilities=dcap,
                                       service_args=['--ignore-ssl-errors=true', '--ssl-protocol=TLSv1'])
        driver.set_window_size(self.__window_size_width, self.__window_size_height)  # set window size
        driver.maximize_window()  # set maximize_window
        driver.set_page_load_timeout(self.__page_load_timeout)  # set time out
        return driver

    @property
    def driver(self):
        ''' 操作句柄 '''
        return self.__driver if self.__driver else None

    def screenshots(self, driver, sleep=None):
        '''
        save screenshots 给模拟浏览器截图
        :param driver: selenium
        :param sleep: sec
        :return:
        '''
        if sleep:
            time.sleep(sleep)
        try:
            driver.save_screenshot("./img/%s.png" % (time.strftime("%Y-%m-%d %X", time.localtime())))
        except Exception:
            pass

    def get_js(self, js_str):
        '''在模拟浏览器中执行 javascript'''
        return self.__driver.execute_script('return %s' % js_str) if self.__driver else None

    def __del__(self):
        ''' 退出模拟的浏览器 quit driver'''
        if not isinstance(self.driver, type(None)):
            self.driver.quit()
