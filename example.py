#!/usr/bin/env python
# -* coding: utf-8 -*
# create by cvno on 2018/1/15 11:52

import GoogleVoice


# 如果需要设置自定义回复，请重写 _initial 方法，不需要的请忽略
class Example(GoogleVoice.Voice):
    def _initial(self):
        ''' 这个函数运行在登录之前, 可以在这里修改一些配置,
         如:
        1. 设置浏览器请求头
        2. 更改登录地址
        3. 设置超时时间
        4. 是否检测新消息
        '''
        self.set_match({'TD': '退订成功'})  # 触发关键词
        self.status['auto'] = True  # 自动回复开关


voice = Example('usernmae', 'passwd', True)
# 在调试的时候建议开启 Debug=True ，它会在终端显示运行日志

# 一定要在这个 flag 为 True 的时候进行操作
while not voice.status['init']:
    continue

# 发送 sms
res1 = voice.send_sms('6128880182', 'Hello World!')
# {"ok":true,"data":{"code":0}}

# 拨打电话
res2 = voice.call('6128880182')
# {"ok":true,"data":{"code":0,"callId":"XXXXXXXXX...."}}

# 取消拨打
res3 = voice.cancel_call(res2['data']['callId'])
# {"ok" : false}

# 获取未读的 sms
for i in voice.unsms:  # 这个方法返回的是一个 list
    res4 = voice.mark(i['id'])  # 标记为已读
    res5 = voice.mark(i['id'], 0)  # 标记为未读

# 获取未读的 voicemail
for i in voice.voicemail:  # 这个方法返回的是一个 list
    print(i['ogg_url'])  # 语音下载地址
    res6 = voice.mark(i['id'])  # 标记为已读
