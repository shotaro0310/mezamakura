import RPi.GPIO as GPIO
import os
import sys
from multiprocessing import Process, Manager
import time
from datetime import datetime as dt
# encoding: utf-8
from argparse import ArgumentParser

from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage
)
import textwrap

app = Flask(__name__)

# チャンネルシークレットとチャンネルアクセストークンの登録
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

# スイッチON・OFF関数の登録
SWITCH_PIN = 23

def SwitchoOff():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SWITCH_PIN, GPIO.OUT)
    GPIO.output(SWITCH_PIN, GPIO.LOW)
    GPIO.cleanup()

def SwitchOn():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SWITCH_PIN, GPIO.OUT)
    GPIO.output(SWITCH_PIN, GPIO.HIGH)

    # 30秒後停止
    time.sleep(30)
    SwitchoOff()
    GPIO.cleanup()


m = Manager()
db = m.dict()

def watcher(d):
    while True:
        try:
            for key, value in d.items() :
                future = [date - dt.now() for date in value]
                future.sort()

                if (len(future) > 0 and future[0].total_seconds()) < 0:
                    temp = db[key]
                    item = temp.pop(0)                          
                    db[key] = temp
                    print('設定時間になりました!\n作動中です')
                    line_bot_api.push_message(key, TextSendMessage(text='設定時間になりました!\n作動中です'))
                    SwitchOn()
                    
        except Exception as e:
            print(e)
        time.sleep(3)


p = Process(name='p1', target=watcher, args=(db, ))
p.start()


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)

def handle_text_message(event):
    text = event.message.text #message from user
    reply = ""

    # print(event)
    # print(event.message)
    # print(dir(event.source))
    # print(vars(event.source))

    # テキストの内容で条件分岐
    if text == '作動':
        # 作動
        SwitchOn()
        # 返事
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage('目覚まし作動')
        )
    elif text == '停止':
        # 停止
        SwitchoOff()
        # 返事
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage('目覚まし停止')
        )
    elif text == '説明':
        s = '''
        LINEからベッドのクッションを操作できる
        「Laspberrybed」です!

        画面下のボタンから、「この説明の確認」、「クッションの作動」、「クッションの停止」
        ができます。

        時刻のみを設定する場合には、
        0:00
        の形式で
        日付も入力するなら、
        2022-1-1 0:00
        の形式で入力してください。
        '''
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(textwrap.dedent(s)[1:-1])
        )

    else:
        inp = text.split(" ")   
        inp.insert(0,event.source.user_id)
        # print(inp)

        try:
            time_set = None
            in_length = len(inp)

            if in_length == 2:  # 0:00の形式の場合
                inp_time = inp[1].split(":")
                print(inp)
                try:
                    hour = int(inp_time[0])
                    minute = 0
                    if len(inp_time) == 2:         
                        minute=int(inp_time[1])
                    time_set = dt.now().replace(hour=hour,minute=minute,second=0)
                    print(inp_time)
                    print(f'time{hour},{minute}')
                    reply = f'time{hour},{minute}'

                except Exception:
                    reply = event.message.text + "は正しい形式ではありません"

            elif in_length == 3:    #2022-1-1 0:00の形式の場合
                inp_date = inp[1].split("-")
                inp_time = inp[2].split(":")

                try:
                    set_year = int(inp_date[0])
                    set_month = int(inp_date[1])
                    set_day = int(inp_date[2])

                    set_hour = int(inp_time[0])
                    set_minute = 0
                    if len(inp_time) == 2:         
                        set_minute=int(inp_time[1])
                        
                    time_set = dt(set_year, set_month, set_day, set_hour, set_minute)

                except Exception:
                    reply = event.message.text + "は正しい形式ではありません"

            else:
                reply = "日付/時間が過ぎています"
            
            if time_set is not None:

                try:
                    db[inp[0]]

                except:
                    db[inp[0]] = []

                if (time_set - dt.now()).total_seconds() > 0:
                    db[inp[0]] = db[inp[0]] + [time_set]
                    print(time_set)
                    alerm_time = time_set.strftime('%Y/%m/%d %H:%M')
                    reply = f'{alerm_time} にアラームが設定されました'

                else:
                    reply = "時間が経過したため、アラームが正常に設定されませんでした"

        except ValueError:
            # 木霊
            reply = "予約された文字列ではありません\n[" + event.message.text + "]"

        line_bot_api.reply_message(event.reply_token,TextSendMessage(text=reply),timeout=10) #返信する


if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port ] [--help]'
    )
    arg_parser.add_argument('-p', '--port', default=8000, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    app.run(debug=options.debug, port=options.port)
