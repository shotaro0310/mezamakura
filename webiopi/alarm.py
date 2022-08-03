import webiopi
import datetime
 
GPIO = webiopi.GPIO

LIGHT = 4    # GPIO4
ALARM_ON = datetime.time(8,0)     # 自動消灯時間 8:00
ALARM_OFF = datetime.time(8,0)     # 自動消灯時間 8:10
 
def setup():
    # GPIO4に出力設定
    GPIO.setFunction(LIGHT, GPIO.OUT)
    # 現在時刻を取得
    now = datetime.time(datetime.datetime.now().hour, datetime.datetime.now().minute)
 
    # 現在時刻とアラームのオンとオフの時間の比較
    if ((now >= ALARM_ON ) and (now <= ALARM_OFF)):
        GPIO.digitalWrite(LIGHT, GPIO.HIGH)
 
def loop():
    # 現在時刻を取得
    now = datetime.datetime.now()
 
    # アラームオン
    if ((now.hour == ALARM_ON.hour) and (now.minute == ALARM_ON.minute) and (now.second == 0)):
        if (GPIO.digitalRead(LIGHT) == GPIO.LOW):
            GPIO.digitalWrite(LIGHT, GPIO.HIGH)
 
    # アラームオフ
    if ((now.hour == ALARM_OFF.hour) and (now.minute == ALARM_OFF.minute) and (now.second == 0)):
        if (GPIO.digitalRead(LIGHT) == GPIO.HIGH):
            GPIO.digitalWrite(LIGHT, GPIO.LOW)
 
    # 1秒間隔で繰り返し
    webiopi.sleep(1)
 
def destroy():
    # webiopi終了時にGPIOをLOWにする
    GPIO.digitalWrite(LIGHT, GPIO.LOW)
 
@webiopi.macro
def getLightHours():
    return "%s;%s" % (ALARM_ON.strftime("%H:%M"),ALARM_OFF.strftime("%H:%M"))
 
@webiopi.macro
def setLightHours(on, off):
    global ALARM_ON, ALARM_OFF
    # 引数を分割
    array_on  = on.split(":")
    array_off = off.split(":")
    # 値の設定
    ALARM_ON  = datetime.time(int(array_on[0]),int(array_on[1]))
    ALARM_OFF = datetime.time(int(array_off[0]),int(array_off[1]))
    return getLightHours()
