# ST0324: Internet Of Things
# CA2 Public Tutorial

# Team: JTF
## Members:
Tan Cheng Kit  
Chong Meng Zhi  
Lee Yu Cai Jordan

# Table of Contents:
- [Section 1 - Overview](#section-1---overview)
- [Section 2 - Hardware](#section-2---hardware)
- [Section 3 - Client](#section-3---client)
- [Section 4 - Server](#section-4---server)
- [Section 5 - References](#section-5---references)

# JTF Smart Fire Alarm
# Section 1 - Overview
## 1.1 About
This project is named Smart Fire Alarm. It was built to detect fire in a room and alert the people as soon as possible. The user will receive Telegram Bot notifications when fire are detected in the room. PiCamera will be activated to take a picture of the current room state when motions are detected by motion sensor. The image taken by PiCamera will be uploaded to S3 bucket and further analyzed by AWS Recognition to detect the number of living things trapped in the room so the firefighters will be able to save them in time. 

The target audience for this application will be the building owners or management. By implementing our project into their buildings, many people can be saved in time when there is fire occurring.
## 1.2 Full Hardware Setup
![alt](resources/hardware.jpg?raw=true)
## 1.3 System Architecture Diagram
![alt](resources/arch.png?raw=true)
## 1.4 Web Application
![alt](resources/webapp.png?raw=true)
Dashboard - Cheng Kit's Room
## 1.5 Telegram Bot Alert
![alt](resources/telegram.png?raw=true)


# Section 2 - Hardware
## 2.1 Hardware List
- Raspberry Pi
- 3x LEDs
- Buzzer
- Adafruit DHT 11 Temperature & Humidity Sensor
- Motion Sensor
- RPI Display
- PiCamera
- 3x 220 Ohms resistor (LED)
- 1x 10k Ohms resistor (DHT 11)
## 2.2 Setup instructions
1) Attach the 3 LEDs to GPIO pins 18, 23 and 24 respectively
2) Attach the buzzer to GPIO pin 20
3) Connect Adafruit DHT 11 to GPIO pin 21
4) Connect motion sensor to GPIO pin 26
5) Connect RPI Display to GPIO pins for I2C connection
6) Connect PiCamera to Raspberry Pi
## 2.3 Fritzing diagram
![alt](resources/fritzing.png?raw=true)


# Section 3 - Client
## 3.1 Code Setup
1) Clone this repository for a copy of the files to your Raspberry Pi
2) Place the AWS CA certificate, IOT private key and IOT cert in `client` folder
3) Open the file `client/jtf_internal/utility.py`
    1) Change the parameters for `mqttsetup` function to match your own files and IOT HTTP endpoint
    2) Change the parameters for `telesetup` function to match your own telegram bot token
4) Open the file `client/jtf_internal/firemanager.py`
    1) Change the global variable `deviceid` to ensure they are unique so there are no conflicts
5) Install python3 requirements for client code
```
pip3 install -r client/requirements.txt
```
6) Place AWS credentials file in `~/.aws/credentials`
## 3.2 Run
1) Change working directory to inside `client`
2) Run the following command
```
python3 jtf-client.py
```


# Section 4 - Server
## 4.1 Code Setup
1) Clone this repository for a copy of the files to your AWS EC2 instance
2) Place the AWS CA certificate, IOT private key and IOT cert in `server` folder
3) Open the file `server/server_utility.py`
    1) Change the parameters for `mqttsetup` function to match your own files and IOT HTTP endpoint
4) Open the file `server/ownServer.py`
    1) Change the global variable `deviceid` to ensure they are unique so there are no conflicts
5) Install python3 requirements for server code
```
pip3 install -r server/requirements.txt
```
6) Place AWS credentials file in `~/.aws/credentials`
## 4.2 Run
- On server side, in order to let the code remain running on AWS EC2 instance even when the shell terminates, run the following commands
```
screen -S server
cd server
python3 ownServer.py
```
- To exit the screen view, press CTRL+A+D keyboard combination
- To return back to the screen view
```
screen -r server
```


# Section 5 - References
https://docs.aws.amazon.com/iot/latest/developerguide/sdk-tutorials.html
https://aws.amazon.com/free/free-tier-faqs
https://docs.aws.amazon.com/iot/latest/developerguide/mqtt.html
https://stackoverflow.com/a/31265602/10004077
https://stackoverflow.com/questions/11994325/how-to-divide-flask-app-into-multiple-py-files
