# Imports
import Adafruit_DHT
from gpiozero import LED, MotionSensor, Buzzer
from picamera import PiCamera
from rpi_lcd import LCD
import time
import json
import datetime
import boto3
from botocore.exceptions import ClientError
from jtf_internal.utility import mqttsetup

# HW Pins
TEMP = 21
LED1 = 18
LED2 = 23
LED3 = 24
MOTION = 26
BUZZER = 20
CAM = None
DISP = None
# Globals
DEVICEID = 1  # todo: reconfigured for diff hosts
REFRESHRATE = 10
TEMPTHRESHOLD = 28.0
FIRETIMEOUT = 60
AWSMQTT = None


# Entrypoint
def firemanager(termlock, pipe):
    """
    The main code that handles fire detection and lifeform detection
    """
    global TEMP
    global MOTION
    global DISP
    global DEVICEID
    global REFRESHRATE
    global TEMPTHRESHOLD
    global FIRETIMEOUT
    global AWSMQTT

    print("Firemanager started")
    try:
        # Init
        __hwinit__()
        AWSMQTT = mqttsetup(DEVICEID)

        # Main handling block
        firestatus = [0, None]
        firetimeout = None
        while True:
            # Monitor termlock signal
            if termlock.acquire(timeout=REFRESHRATE):
                # Signal stop from process
                break

            # Read temp and upload
            # Used to monitor room temp and monitor changes in fire
            h, t = Adafruit_DHT.read_retry(11, TEMP)
            __publish_temp__(t)
            print(f"Published temp {t}")

            # Check for fire and updates when there is a change to fire status
            # Note: under normal circumstances something like a smoke detector shd be used here
            if t >= TEMPTHRESHOLD:
                # FIRE DETECTED - 1
                if firestatus[0] != 1:
                    # Check if fire is reoccurring
                    if firestatus[0] == 2:
                        firestatus[1] = 0  # Recurring fire
                    else:
                        firestatus[1] = 1  # New fire
                    # Set main code
                    firestatus[0] = 1  # Current detected fire code
                    # Activate hardware
                    __fire__()
                    # Send update to main process
                    pipe.send(firestatus)
                    print("Fire detected")
            else:
                # Fire subsiding - 2
                if firestatus[0] == 1:
                    firestatus[0] = 2  # Fire subsiding code
                    # Set fire timeout time
                    firetimeout = time.time() + FIRETIMEOUT
                    # Activate hardware
                    __smoldering__()
                    # Send update to main process
                    pipe.send(firestatus)
                    print("Fire subsiding")

                # Fire stopped - 3
                elif firestatus[0] == 2:
                    if time.time() > firetimeout:
                        firestatus[0] = 3  # Fire stopped code
                        firestatus[1] = None
                        # Activate hardware
                        __firestop__()
                        # Send update to main process
                        pipe.send(firestatus)
                        print("Fire stopped")
                        # Reset
                        firestatus[0] = 0

            # Check for lifeform if fire
            if firestatus[0] == 1:
                # Check for motion
                if MOTION.is_active:
                    # Take pic of area and upload to S3
                    filename = __lifeform_check__()

                    # Send update to main process
                    pipe.send([4, filename])
                    print(f"Possible lifeform in {filename}")
                else:
                    print("Clear of lifeforms")

        # Cleanup
        # AWSMQTT.disconnect()
        print("Firemanager module terminated")
    except Exception as e:
        print("Exception raised in firemanager module")
        termlock.release()
    finally:
        DISP.clear()
        pipe.send([0, None])
        pipe.close()
        print("Pipe closed")


# Hardware handling
def __fire__():
    global LED1
    global LED2
    global LED3
    global BUZZER

    LED1.blink()
    LED2.blink()
    LED3.blink()
    BUZZER.blink(on_time=1, off_time=3)
    __display_write__("Fire Detected, Rmb 2 git push!")


def __smoldering__():
    global LED1
    global LED2
    global LED3
    global BUZZER

    LED1.blink(on_time=1, off_time=3)
    LED2.off()
    LED3.blink(on_time=1, off_time=3)
    BUZZER.off()
    __display_write__("Fire is out, remain alert.")


def __firestop__():
    global LED1
    global LED2
    global LED3
    global BUZZER

    LED1.off()
    LED2.off()
    LED3.off()
    BUZZER.off()
    __display_write__("Status: Normal")


def __display_write__(msg):
    global DISP

    DISP.clear()
    DISP.text(msg, 1)


def __lifeform_check__():
    global CAM
    global DEVICEID

    # Variable definition
    timestr = datetime.datetime.now().strftime("%d-%m-%Y_%H:%M:%S")
    path = "./photo/"
    filename = "rpi{}_{}.jpg".format(DEVICEID, timestr)
    fullpath = path + filename

    # Take pic, upload
    CAM.capture(fullpath)
    __bucket_file_upload__(fullpath, filename)

    # Return uploaded filename
    return filename


# Utility
def __hwinit__():
    global TEMP
    global LED1
    global LED2
    global LED3
    global MOTION
    global BUZZER
    global CAM
    global DISP

    # Init hw
    LED1 = LED(LED1)
    LED2 = LED(LED2)
    LED3 = LED(LED3)
    MOTION = MotionSensor(MOTION, sample_rate=5, queue_len=1)
    BUZZER = Buzzer(BUZZER)

    # Additional hwinit
    Adafruit_DHT.read_retry(11, TEMP)
    CAM = PiCamera()
    DISP = LCD(width=16, rows=2)
    __display_write__("Status: Normal")


def __publish_temp__(temp):
    global DEVICEID
    global AWSMQTT

    # Variable definitions
    qoslvl = 0
    topic = "jtf/rpi/temperature"
    data = {
        "deviceid": DEVICEID,
        "datetime": time.time(),
        "temp": temp
    }

    # Send
    AWSMQTT.publish(topic, json.dumps(data), qoslvl)


def __bucket_file_upload__(filepath, filename):
    # Variable definition
    bucket = "ca2-iot-picamfiles"
    location = {"LocationConstraint": "ap-southeast-1"}

    # Bucket verification (and creation)
    s3 = boto3.resource("s3")
    exists = True
    try:
        s3.meta.client.head_bucket(Bucket=bucket)
    except ClientError as e:
        ecode = int(e.response["Error"]["Code"])
        if ecode == 404:
            exists = False
    if not exists:
        s3.create_bucket(Bucket=bucket, CreateBucketConfiguration=location)

    # Upload file
    s3.Object(bucket, filename).put(Body=open(filepath, "rb"))
