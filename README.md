# 20200807 不再维护
>为了帮助保护您的帐号，Google 不允许您通过某些浏览器登录。Google 可能会阻止从存在以下情况的浏览器登录：

- 不支持 JavaScript 或者已关闭 JavaScript。
- 添加了不安全或不受支持的扩展程序。
- **使用自动化测试框架**。
- 嵌入在其他应用中。

详情查看： [here](https://support.google.com/accounts/answer/7675428?hl=zh-Hans)
仅作为学习用途
```shell script
python setup.py sdist bdist_wheel # 打包成wheel
```

~~使`Google Voice`号码免于被回收~~

### 封装 Docker 2018/11/11
封装到 docker， 并每周向指定号码发送信息

```sh
# run
docker run -d -p 3280:5000 -e "GV_USR=<your email>" -e "GV_PWD=<your passwd>" -e "GVAPI_IS_DEV=true" --restart always cvno/gv
```

在指令中`GV_USR`和`GV_PWD`填入自己的邮箱和密码，稍等片刻后访问`ip:3280/sms/13212969527/gv:0.1`成功后会返回数据。

`ip:3280/sms/13212969527/gv:0.1`向`13212969527`这个号码发送`sms`信息，内容为`gv:0.1`

```sh
# 自行build
docker build -t <your id>/gv:0.1 .
```

**注意**:自行`build`后如果要上传一定要把`docker`仓库设置为私有！！！否则任何人都可以看到你的镜像将暴露你的帐号密码。

# GV Python API

使用 Python3 来操作 Google Voice 的 API。[English](/en)（未完成）

功能列表:

- 发送 SMS
- 拨打电话
- 取消拨打电话
- 标记为已读或未读
- 下载语音留言
- 后台自动检测是否有新信息
- 根据 SMS 的设置自动回复


~~它也可能是一个廉价的短信验证码方案。~~

**依赖:**
- 浏览器 [PhantomJS](http://phantomjs.org/download.html) | [geckodriver](https://github.com/mozilla/geckodriver) | [chromedriver](https://chromedriver.chromium.org/)

# 开发使用

```python
from gvapi import Voice


# 如果需要设置自定义回复，请重写 _initial 方法，不需要的请忽略
class Example(Voice):
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
res1 = voice.send_sms('+18566712333', 'Hello World!')
# {"ok":true,"data":{"code":0}}

# 拨打电话
res2 = voice.call('+18566712333')
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
```

***注意：***
1. Google Voice 是使用 C2C 模式拨打电话的，也就是说需要转接号码，如果你账号已经绑定了号码，那么程序会自动处理。
2. 获取新消息处理之后，建议直接删除，或备份到数据库；如果不删除会影响新消息的数据处理。

# 声明
如果 Google 更改登录机制，或弃用旧版，本代码可能会不支持，如果你下载此代码，代表您同意自行承担使用风险。

# 许可
by [Git @kentio](https://github.com/kentio/)
See LICENSE
