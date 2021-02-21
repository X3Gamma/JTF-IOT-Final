import sys
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from telepot import Bot


def eprint(*args, sep=' ', end='\n'):
    print(*args, sep=sep, end=end, file=sys.stderr)


def mqttsetup(deviceid):
    # AWS Params
    host = "host.iot.ap-southeast-1.amazonaws.com"
    rootca = "AmazonRootCA1.pem"
    privkey = "private.pem.key"
    cert = "certificate.pem.crt"

    # Basic mqtt config
    mqtt = AWSIoTMQTTClient(f"JTF Fire Alarm {deviceid}")
    mqtt.configureEndpoint(host, 8883)
    mqtt.configureCredentials(rootca, privkey, cert)

    # Advanced mqtt config
    mqtt.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
    mqtt.configureDrainingFrequency(2)  # Draining: 2 Hz
    mqtt.configureConnectDisconnectTimeout(10)  # 10 sec
    mqtt.configureMQTTOperationTimeout(5)  # 5 sec

    # Verify connection
    try:
        mqtt.connect()
        return mqtt
    except Exception as e:
        return None


def telesetup():
    # Telegram Params
    # todo: remove when uploading to public
    token = ""

    # Initialize bot
    telebot = Bot(token)

    # Verify connection
    try:
        telebot.getMe()
        return telebot
    except Exception as e:
        return None
