# Imports
import sys
import multiprocessing
import json
from gpiozero import LED, Buzzer
# JTF Imports
from jtf_internal import firemanager
from jtf_internal.utility import eprint, mqttsetup, telesetup

# HW Pins
LED1 = 18
LED2 = 23
LED3 = 24
BUZZER = 20
# Globals
DEVICEID = firemanager.DEVICEID
TERMLOCK = True
AWSMQTT = None
TELEBOT = None


# Main functions
def bootstrap():
    global DEVICEID
    global TERMLOCK
    global AWSMQTT
    global TELEBOT

    # Init
    TERMLOCK = multiprocessing.Lock()
    rp, wp = multiprocessing.Pipe()

    # Start mqtt
    AWSMQTT = mqttsetup(DEVICEID)
    if not AWSMQTT:
        eprint("Failed to connect to mqtt")
        sys.exit(1)

    # Start telegram
    TELEBOT = telesetup()
    if not TELEBOT:
        eprint("Failed to connect to telegram")
        sys.exit(1)

    # Start fire manager
    TERMLOCK.acquire(block=False)
    fmproc = multiprocessing.Process(target=firemanager.firemanager, name=f"JTF Fire Alarm {DEVICEID}", daemon=True,
                                     args=(TERMLOCK, wp))
    fmproc.start()
    if TERMLOCK.acquire(timeout=5):
        eprint("JTF Fire Alarm failed to start")
        sys.exit(1)

    # Init hardware
    __hwinit__()

    # Register to server control
    AWSMQTT.subscribe(f"jtf/rpi/{DEVICEID}/control", 0, servermanager)

    # Main Block
    if firewatch(rp):
        # Manual stop
        if not TERMLOCK.acquire(block=False):
            TERMLOCK.release()
        print("Manually sent terminate signal")

    # Exit
    try:
        # AWSMQTT.disconnect()
        fmproc.join()
    except Exception as e:
        pass
    finally:
        fmproc.close()
    rp.close()
    print("JTF Smart Fire Alarm Terminating")


def firewatch(pipe):
    """
    Alert manager for firemanager module
    """
    print("Firewatch started")
    while True:
        try:
            if pipe.poll(timeout=5):
                code, data = pipe.recv()

                # Fire
                if code == 1:
                    # 1 - new fire, 0 - recurring
                    __publish_status__(code, data)
                    if data:
                        __telealert__("A fire has re-occurred!")
                    else:
                        __telealert__("A fire has occurred!")

                # Subsiding
                elif code == 2:
                    __publish_status__(code, data)
                    __telealert__("The fire is subsiding.")

                # Stopped
                elif code == 3:
                    __publish_status__(code, None)
                    __telealert__("The fire has stopped.")

                # Lifeform detection
                elif code == 4:
                    # "data" is the filename of suspect pic in s3 bucket
                    __publish_status__(code, data)
                    __telealert__(f"Possible lifeform detected. Check S3 file, {data}.")

                # Exit
                elif code == 0:
                    "Firewatch exiting"
                    raise EOFError

                # Unrecognized code
                else:
                    raise RuntimeError

        except (BrokenPipeError, EOFError) as e:
            break
        except KeyboardInterrupt:
            return 1
        except Exception:
            eprint("Error handling data from firemanager")


# Control function
def servermanager(client, userdata, message):
    """
    Callback manager for ec2 control
    """
    global TERMLOCK

    try:
        # Payload should be a json dumped dict
        raw = json.loads(message.payload)
        code = raw["code"]
        data = raw["data"]

        # LED Test
        if code == 1:
            if data == 1 or data == 0:
                __led_test__(data)

        # Buzzer Test
        elif code == 2:
            if data == 1 or data == 0:
                __buzzer_test__(data)

        # Terminate
        elif code == 0:
            if not TERMLOCK.acquire(block=False):
                TERMLOCK.release()
            print("Terminate signal received")

        # Unknown command
        else:
            raise RuntimeError
    except Exception as e:
        eprint("Error handling command on control channel")


def __led_test__(sw):
    global LED1
    global LED2
    global LED3

    # Toggle on
    if sw:
        LED1.on()
        LED2.on()
        LED3.on()
    # Toggle off
    else:
        LED1.off()
        LED2.off()
        LED3.off()


def __buzzer_test__(sw):
    global BUZZER

    # Toggle on
    if sw:
        BUZZER.on()
    # Toggle off
    else:
        BUZZER.off()


# Utility
def __publish_status__(code, data):
    global DEVICEID
    global AWSMQTT

    # Variable definitions
    qoslvl = 0
    topic = "jtf/rpi/message"
    data = {
        "deviceid": DEVICEID,
        "code": code,
        "data": data
    }

    # Send
    AWSMQTT.publish(topic, json.dumps(data), qoslvl)


def __telealert__(msg):
    global DEVICEID
    global TELEBOT

    # Variable definitions
    userids = [909501279]
    msg = f"rpi{DEVICEID}: {msg}"

    # Send
    for id in userids:
        TELEBOT.sendMessage(id, msg)


def __hwinit__():
    global LED1
    global LED2
    global LED3
    global BUZZER

    # Init hw
    LED1 = LED(LED1)
    LED2 = LED(LED2)
    LED3 = LED(LED3)
    BUZZER = Buzzer(BUZZER)


if __name__ == "__main__":
    if sys.version_info[0] != 3 or sys.version_info[1] < 7:
        eprint("Python version 3.7 and below is not supported.")
        sys.exit(1)

    # Entrypoint
    bootstrap()
