from gevent.pywsgi import WSGIServer
from flask import Flask, render_template, redirect, url_for, jsonify, request
from server_utility import mqttsetup, eprint
from dynamodb import retrieve_from_dynamodb
from dynamodb import data_to_json
import sys, json
import boto3
from PIL import Image
'''
Global variables here
'''
JTFFLASK = None
app = Flask(__name__)
DEVICEID = 3
AWSMQTT = None
qoslvl = 0
BUCKET = 'ca2-iot-picamfiles'


'''
Setting up MQTT
'''
def awsmqtt():
    global AWSMQTT

    # Start mqtt
    AWSMQTT = mqttsetup(DEVICEID)
    if not AWSMQTT:
        eprint("Failed to connect to mqtt")
        sys.exit(1)


'''
Flask API
'''
def webHere():
    global JTFFLASK

    flaskcrt = "certs/JTFIotEC2.crt"
    flaskkey = "certs/JTFIotEC2.key"

    try:
        JTFFLASK = WSGIServer(("0.0.0.0", 25535), app, log=None, error_log=None, certfile=flaskcrt, keyfile=flaskkey)
        print("starting")
        JTFFLASK.serve_forever()
    except KeyboardInterrupt:
        JTFFLASK.stop()
    finally:
        print("stopping")


# Flask routes
@app.route("/")
def indexpage():
    return redirect(url_for("homepage"), code=302)


@app.route("/jtf")
def homepage():
    return render_template("dashboard.html")


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


'''
LED and Buzzer Test
Code: 1 is LED, 2 is Buzzer
Data: 1 is On, 0 is Off
'''
@app.route("/jtf/api/led/1/<status>", methods=['GET', 'POST'])
def ledTest(status):
    global qoslvl
    global AWSMQTT

    print(status)
    status = int(status)

    topic = "jtf/rpi/1/control"
    # code must be 1 (LED)
    data = {
        "code": int(1),
        "data": status
    }

    AWSMQTT.publish(topic, json.dumps(data), qoslvl)
    templatedata = {
        "title": "LED Status",
        "response": status
    }
    return render_template("status.html", **templatedata)

@app.route("/jtf/api/led/2/<status>", methods=['GET', 'POST'])
def ledTest2(status):
    global qoslvl
    global AWSMQTT

    status = int(status)
    topic = "jtf/rpi/2/control"
    # code must be 1 (LED)
    data = {
        "code": int(1),
        "data": status
    }

    AWSMQTT.publish(topic, json.dumps(data), qoslvl)
    templatedata = {
        "title": "LED Status",
        "response": status
    }
    return render_template("status.html", **templatedata)

@app.route("/jtf/api/led/3/<status>", methods=['GET', 'POST'])
def ledTest3(status):
    global qoslvl
    global AWSMQTT

    status = int(status)
    topic = "jtf/rpi/3/control"
    # code must be 1 (LED)
    data = {
        "code": int(1),
        "data": status
    }

    AWSMQTT.publish(topic, json.dumps(data), qoslvl)
    templatedata = {
        "title": "LED Status",
        "response": status
    }
    return render_template("status.html", **templatedata)


@app.route("/jtf/api/buzzer/1/<status>", methods=['GET', 'POST'])
def buzPin(status):
    global qoslvl
    global AWSMQTT

    status = int(status)
    topic = "jtf/rpi/1/control"
    # code must be 2 (LED)
    data = {
        "code": int(2),
        "data": status
    }

    AWSMQTT.publish(topic, json.dumps(data), qoslvl)
    templatedata = {
        "title": "Buzzer Status",
        "response": status
    }
    return render_template("status.html", **templatedata)


@app.route("/jtf/api/buzzer/2/<status>", methods=['GET', 'POST'])
def buzPin2(status):
    global qoslvl
    global AWSMQTT

    status = int(status)
    topic = "jtf/rpi/2/control"
    # code must be 2 (LED)
    data = {
        "code": int(2),
        "data": status
    }

    AWSMQTT.publish(topic, json.dumps(data), qoslvl)
    templatedata = {
        "title": "Buzzer Status",
        "response": status
    }
    return render_template("status.html", **templatedata)

@app.route("/jtf/api/buzzer/3/<status>", methods=['GET', 'POST'])
def buzPin3(status):
    global qoslvl
    global AWSMQTT

    status = int(status)
    topic = "jtf/rpi/3/control"
    # code must be 2 (LED)
    data = {
        "code": int(2),
        "data": status
    }

    AWSMQTT.publish(topic, json.dumps(data), qoslvl)
    templatedata = {
        "title": "Buzzer Status",
        "response": status
    }
    return render_template("status.html", **templatedata)


@app.route("/jtf/api/special/<id>")
def terminateRPI(id):
    global qoslvl
    global AWSMQTT

    topic = f"jtf/rpi/{id}/control"
    data = {
        "code": int(0),
        "data": None
    }

    AWSMQTT.publish(topic, json.dumps(data), qoslvl)
    templatedata = {
        "title": "RPI Status",
        "response": "RPI is closed."
    }
    return render_template("status.html", **templatedata)


'''
Call function from dynamodb.py to get temperature
Jsonify the retrieved temperature and send over to front-end
'''
@app.route("/jtf/api/getdata",methods=['POST', 'GET'])
def tempapi():
    if request.method == 'POST':
        try:
            data = {'chart_data': data_to_json(retrieve_from_dynamodb()),
                    'title': "JTF Data"}
            return jsonify(data)
        except:
            print(sys.exc_info()[0])
            print(sys.exc_info()[1])


'''
1) Subcribe to jtf/rpi/message
2) If 4, retrieve from bucket S3
3) Do rekognition
4) Detect how many faces
5) Display the image 
'''
def detect_faces(bucket, key, max_labels=10, min_confidence=90, region="ap-southeast-1"):
    rekognition = boto3.client("rekognition", region)
    response = rekognition.detect_faces(
        Image={
            "S3Object": {
                "Bucket": bucket,
                "Name": key,
            }},
        Attributes=['ALL']
    )
    return response['FaceDetails']


# Control function
def servermanager(client, userdata, message):
    global DEVICEID

    try:
        # Payload should be a json dumped dict
        raw = json.loads(message.payload)
        if raw["deviceid"] == DEVICEID:
            code = raw["code"]
            data = raw["data"]

            if code == 4:
                facedetected = runRekog(data)
                showRekognition(data, facedetected)
                return data, facedetected
    except Exception as e:
        eprint("Error handling command on control channel")


def retrieveFilename():
    global AWSMQTT
    global qoslvl

    AWSMQTT.subscribe("jtf/rpi/message", qoslvl, servermanager)


def runRekog(filename):
    global BUCKET
    facedetected = 0
    for faceDetail in detect_faces(BUCKET, filename):
        facedetected += 1
        ageLow = faceDetail['AgeRange']['Low']
        ageHigh = faceDetail['AgeRange']['High']
        print('Age between {} and {} years old'.format(ageLow, ageHigh))
        print('Here are the other attributes:')
        print(json.dumps(faceDetail, indent=4, sort_keys=True))
    return facedetected


# todo: retrieve img from bucket and display
def showRekognition(file_name, facedetected):
    if not file_name:
        data = {"peopleDetected": "No fire detected", "image": ""}
        return jsonify(data)

    s3 = boto3.client('s3')
    s3.download_file(BUCKET, file_name, 'capture.jpg')
    imagefile = Image.open(r"capture.jpg")

    # Detect face information: https://docs.aws.amazon.com/rekognition/latest/dg/faces-detect-images.html
    message = "Number of people detected: " + str(facedetected)

    if facedetected > 0:
        data = {"peopleDetected": message, "image": imagefile}
        return jsonify(data)
    else:
        data = {"peopleDetected": "No people detected", "image": imagefile}
        return jsonify(data)

if __name__ == "__main__":
    awsmqtt()
    retrieveFilename()
    webHere()
