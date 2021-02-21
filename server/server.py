from flask import Flask, render_template, jsonify, request, Response, redirect, url_for
import sys
import json
import numpy
import datetime
import decimal
import gevent
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import gevent.monkey
from gevent.pywsgi import WSGIServer

# gevent.monkey.patch_all()

from PIL import Image
import boto3, botocore
from datetime import date
from time import sleep


class GenericEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, numpy.generic):
            return numpy.asscalar(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        else:
            return json.JSONEncoder.default(self, obj)


def data_to_json(data):
    json_data = json.dumps(data, cls=GenericEncoder)
    return json_data


def eprint(*args, sep=' ', end='\n'):
    print(*args, sep=sep, end=end, file=sys.stderr)


app = Flask(__name__)


@app.route("/")
def indexpage():
    # return render_template('dashboard.html')
    return redirect(url_for("homepage"), code=302)


@app.route("/jtf")
def homepage():
    return render_template('dashboard2.html')


@app.route("/jtf2")
def dashboard2():
    return render_template("dashboard2.html")


@app.route("/jtf3")
def dashboard3():
    return render_template("dashboard3.html")


@app.route("/jtf/api/init/0")
def shutdownapi():
    JTFFLASK.stop()

    templatedata = {
        "title": "Server Status",
        "response": "Server has shutdown"
    }
    return render_template("status.html", **templatedata)


# LEDs and Buzzer Control for web application
def customCallback(client, userdata, message):
    print("Received a new message: ")
    print(message.payload)
    print("from topic: ")
    print(message.topic)
    print("--------------\n\n")


# host = "a538th5v5suq-ats.iot.ap-southeast-1.amazonaws.com"
# rootca = "AmazonRootCA1.pem"
# cert = "c59cd46826-certificate.pem.crt"
# privkey = "c59cd46826-private.pem.key"


# todo: Change DEVICEID
global DEVICEID
global qoslvl
global AWSMQTT
DEVICEID = 2
qoslvl = 0


def mqttsetup(DEVICEID):
    # AWS Params
    host = "a538th5v5suq-ats.iot.ap-southeast-1.amazonaws.com"
    rootca = "certs/AmazonRootCA1.pem"
    privkey = "certs/c59cd46826-private.pem.key"
    cert = "certs/c59cd46826-certificate.pem.crt"

    # Basic mqtt config
    mqtt = AWSIoTMQTTClient(f"JTF Fire Alarm {DEVICEID}")
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


AWSMQTT = mqttsetup(DEVICEID)
if not AWSMQTT:
    eprint("Failed to connect to mqtt")
    sys.exit(1)


# code 1 is LED, 2 is Buz. data 1 On, 0 Off
def ledOn():
    message = {"code": 1, "data": 1}
    AWSMQTT.publish(f"jtf/rpt/{DEVICEID}/control", json.dumps(message), qoslvl)
    return "LEDs are On"


def ledOff():
    message = {"code": 1, "data": 0}
    AWSMQTT.publish(f"jtf/rpt/{DEVICEID}/control", json.dumps(message), qoslvl)
    return "LEDs are Off"


def buzOn():
    message = {"code": 2, "data": 1}
    AWSMQTT.publish(f"jtf/rpt/{DEVICEID}/control", json.dumps(message), qoslvl)
    return "Buzzer is On"


def buzOff():
    message = {"code": 2, "data": 0}
    AWSMQTT.publish(f"jtf/rpt/{DEVICEID}/control", json.dumps(message), qoslvl)
    return "Buzzer is Off"


# Get response from web interface and return
@app.route("/writeLED/<status>")
def writePin(status):
    if status == 'LEDsOn':
        response = ledOn()
    if status == 'LEDsOff':
        response = ledOff()

    return response


# Get response from web interface and return
@app.route("/writeBuzzer/<status>")
def buzPin(status):
    if status == 'buzOn':
        response = buzOn()
    if status == 'buzOff':
        response = buzOff()

    return response


# End of LEDs and Buzzer Control for web application

# Send past temperature with datetime from dynamoDB
@app.route("/showDHTData", methods=['POST', 'GET'])
def showDHTData():
    try:
        import boto3
        from boto3.dynamodb.conditions import Key, Attr

        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('CA2-iot')
        startdate = '2021-02'

        response = table.query(
            KeyConditionExpression=Key('deviceid').eq(DEVICEID)
                                   & Key('datetime').begins_with(startdate),
            ScanIndexForward=False
        )

        items = response['Items']
        n = 10  # limit to last 10 items
        data = items[:n]
        data_reversed = data[::-1]
        last_data = items[-1]
        data = {'chart_data': data_to_json(data_reversed), 'real_time': data_to_json(last_data),
                'title': "Temperature Data"}
        return jsonify(data)

    except:
        import sys
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])


# Recognition - Analyze picture taken by deployed fire alarms
def detect_faces(bucket, key, max_labels=10, min_confidence=90, region="us-east-1"):
    rekognition = boto3.client("rekognition", region)
    response = rekognition.detect_faces(
        Image={
            "S3Object": {
                "Bucket": bucket,
                "Name": key,
            }
        },
        Attributes=['ALL']
    )
    return response['FaceDetails']


# To get image file name from S3
def servermanager(client, userdata, message):
    """
    Callback manager for ec2 control
    """
    try:
        # Payload should be a json dumped dict
        raw = json.loads(message.payload)
        code = raw["code"]
        data = raw["data"]

        # Getting the image file name in S3 Bucket
        if code == 4:
            return data

    except Exception as e:
        eprint("Error handling command on control channel")


# Send image and Rekognition results (whether there are people in image)
@app.route("/showRekognition", methods=['POST', 'GET'])
def showRekognition():
    file_name = AWSMQTT.subscribe(f"jtf/rpi/message", 0, servermanager)
    if not file_name:
        data = {"peopleDetected": "No fire detected", "image": ""}
        return jsonify(data)
    BUCKET = 'ca2-iot-picamfiles'

    if detect_faces(BUCKET, file_name):
        s3 = boto3.client('s3')
        s3.download_file(BUCKET, file_name, 'capture.jpg')
        imagefile = Image.open(r"capture.jpg")
        facedetected = 0

        # Detect face information: https://docs.aws.amazon.com/rekognition/latest/dg/faces-detect-images.html
        for faceDetail in detect_faces(BUCKET, file_name):
            facedetected += 1
        message = "Number of people detected: " + str(facedetected)

        if facedetected > 0:
            data = {"peopleDetected": message, "image": imagefile}
            return jsonify(data)
        else:
            data = {"peopleDetected": "No people detected", "image": imagefile}
            return jsonify(data)


if __name__ == '__main__':
    global JTFFLASK
    flaskcrt = "certs/JTFIotEC2.crt"
    flaskkey = "certs/JTFIotEC2.key"
    try:
        JTFFLASK = WSGIServer(("0.0.0.0", 25535), app, log=None, error_log=None, certfile=flaskcrt,
                              keyfile=flaskkey)
        print("starting")
        JTFFLASK.serve_forever()
    except KeyboardInterrupt:
        JTFFLASK.stop()
    finally:
        print("stopping")


