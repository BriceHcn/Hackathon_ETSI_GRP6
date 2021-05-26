# Version 1.1

import requests
import json
from flask import Flask
from flask import request
from flask import Response
import sys
import random
import configparser
from pyowm import OWM
from pyowm.utils import timestamps
from datetime import timedelta
from pathlib import Path

# /////////////// Parameters /////////////////
config = configparser.ConfigParser()
path = Path(__file__).parent / "default.json"
with open(path, 'r') as f:
    config = json.load(f)
# CSE Params
csePoA = "http://" + config["cse"]["ip"] + ":" + str(config["cse"]["port"])
cseName = config["cse"]["name"]
cseRelease = config["cse"]["release"]
poa_in_nu = config["cse"]["poa_in_nu"]
# AE params
monitorId = config["monitor"]["id"]
monitorIP = config["monitor"]["ip"]
monitorPort = config["monitor"]["port"]
monitorPoA = "http://" + monitorIP + ":" + str(monitorPort)

humidityThreshold = config["HumiditySensor"]["humidityThreshold"]
isLedOn = config["LedActuator"]["isLedOn"]
requestNr = 0

sensorToMonitor = ""
actuatorToTrigger = ""


def createSUB():
    global requestNr
    global cseRelease
    global poa_in_nu
    headers = {
        'Content-Type': 'application/json;ty=23',
        'X-M2M-Origin': monitorId,
        "X-M2M-RI": "req" + str(requestNr),
    }

    if (cseRelease != "1"):
        headers.update({"X-M2M-RVI": cseRelease})

    notificationUri = [cseName + "/Monitor"]
    if (poa_in_nu):
        notificationUri = [monitorPoA]

    response = requests.post(csePoA + '/' + cseName + "/" + sensorToMonitor + '/DATA',
                             json={
                                 "m2m:sub": {
                                     "rn": "SUB_Monitor",
                                     "nu": notificationUri,
                                     "nct": 1,
                                     "enc": {
                                         "net": [3]
                                     }
                                 }
                             },
                             headers=headers
                             )
    requestNr += 1
    if response.status_code != 201:
        print("SUB Creation error : ", response.text)
    else:
        print("SUB Creation :", response.status_code)


def createAE():
    global requestNr
    global cseRelease
    headers = {
        'Content-Type': 'application/json;ty=2',
        'X-M2M-Origin': monitorId,
        "X-M2M-RI": "req" + str(requestNr),
    }
    ae_json = {
        "m2m:ae": {
            "rn": "Monitor",
            "api": "Norg.demo.monitor-app",
            "rr": True,
            "poa": [monitorPoA]
        }
    }
    if (cseRelease != "1"):
        headers.update({"X-M2M-RVI": cseRelease})
        ae_json['m2m:ae'].update({"srv": [cseRelease]})

    response = requests.post(csePoA + "/" + cseName,
                             json=ae_json,
                             headers=headers
                             )
    requestNr += 1
    if response.status_code != 201:
        print("AE Creation error : ", response.text)
    else:
        print("AE Creation :", response.status_code)
    createSUB()


def createCIN(actuatorName, commandName):
    global requestNr
    global cseRelease
    headers = {
        'Content-Type': 'application/json;ty=4',
        'X-M2M-Origin': monitorId,
        "X-M2M-RI": "req" + str(requestNr),
    }

    if (cseRelease != "1"):
        headers.update({"X-M2M-RVI": cseRelease})

    response = requests.post(csePoA + "/" + cseName + "/" + actuatorName + '/COMMAND',
                             json={
                                 "m2m:cin": {
                                     "con": commandName
                                 }
                             },
                             headers=headers
                             )
    requestNr += 1
    if response.status_code != 201:
        print("CIN Creation error : ", response.text)
    else:
        print("CIN Creation :", response.status_code)


api = Flask(__name__)


@api.route('/', methods=['POST'])
def processNotification():
    global isLedOn
    notificationJSON = request.json
    sensorValue = int(notificationJSON['m2m:sgn']['nev']['rep']['m2m:cin']['con'])
    print("Receieved sensor value : ", sensorValue)

    # demo selection : begin
    if (sensorToMonitor == "HumiditySensor") and (actuatorToTrigger == "LedActuator"):
        commandLedHumidity(sensorValue)
    else:
        print("Demo not implemented")
    # demo selection : end

    response = Response('')
    response.headers["X-M2M-RSC"] = 2000
    if (cseRelease != "1"):
        response.headers["X-M2M-RVI"] = cseRelease
    return response


def commandLedHumidity(sensorValue):
    print("seuil humdité = %d" % (humidityThreshold))
    global isLedOn

    rainIn8hours = RainAtLocationInXHours(config['location']['city'] + ',' + config['location']['country'],  config['delay']['rainDelay'])

    # if (sensorValue > humidityThreshold) and (isLedOn == True):
    if sensorValue > humidityThreshold:
        print("High humidity => Switch OFF the led")
        createCIN(actuatorToTrigger, "[switchOff]")
        isLedOn = False
    # elif (sensorValue < humidityThreshold) and (isLedOn == False):
    elif (sensorValue < humidityThreshold) :
        if rainIn8hours :
            #pluie dans les 8 prochaines heures donc rien
            print("Low humidity but rain in next "+str(config['delay']['rainDelay'])+" hours @"+config['location']['city']+" => Switch OFF the led")
            createCIN(actuatorToTrigger, "[switchOff]")
            isLedOn = False
        else :
            # pas de pluie dans les 8 prochaines heures donc on arrose
            print("Low humidity and no rain in next "+str(config['delay']['rainDelay'])+" hours @"+config['location']['city']+" => Switch ON the led")
            createCIN(actuatorToTrigger, "[switchOn]")
            isLedOn = True

    else:
        print("Nothing to do")


def commandActuator(args):
    global actuatorToTrigger
    requestNr = random.randint(0, 1000)
    print("The command " + args.command + " will be sent to the actuator " + args.actuator)
    actuatorToTrigger = args.actuator + "Actuator"
    createCIN(actuatorToTrigger, "[" + args.command + "]")
    sys.exit()


def getAll(args):
    global requestNr
    global cseRelease

    requestNr = random.randint(0, 1000)
    print("Sending request >>> ")
    headers = {
        'X-M2M-Origin': monitorId,
        "X-M2M-RI": "req" + str(requestNr),
        'Accept': 'application/json'
    }
    if (cseRelease != "1"):
        headers.update({"X-M2M-RVI": cseRelease})

    response = requests.get(csePoA + "/" + cseName + "/" + args.sensor + "Sensor/DATA" + '?rcn=4',
                            headers=headers)

    print("<<< Response received ! ")

    if response.status_code != 200:
        print("Error = ", response.text)
    else:
        print("Effective content of CINs = ")
        contentInstanceInJSON = json.loads(response.content)
        for elt in contentInstanceInJSON['m2m:cnt']['m2m:cin']:
            print("   " + elt['con'])

    sys.exit()


def getLatest(args):
    global requestNr
    global cseRelease
    requestNr = random.randint(0, 1000)
    print("Sending request >>> ")
    headers = {
        'X-M2M-Origin': monitorId,
        "X-M2M-RI": "req" + str(requestNr),
        'Accept': 'application/json'
    }
    if (cseRelease != "1"):
        headers.update({"X-M2M-RVI": cseRelease})

    response = requests.get(csePoA + "/" + cseName + "/" + args.sensor + "Sensor/DATA/la",
                            headers=headers)

    requestNr += 1
    print("<<< Response received ! ")

    if response.status_code != 200:
        print("Error = ", response.text)
    else:
        cin = json.loads(response.content)
        print("Effective content of CIN = ", cin['m2m:cin']['con'])

    sys.exit()


def getParameters():
    import argparse
    global sensorToMonitor, actuatorToTrigger

    # Command-line parsing
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--sensor", choices=["Humidity"], default="Humidity", help='Sensor to be monitored')
    parser.add_argument("-a", "--actuator", choices=["Led", "Display", "Servo"], default="Led",
                        help='Actuator to trigger')

    # Subcommands command-line parsing
    subparsers = parser.add_subparsers(required=False, help="Subcommands")
    # "commandActuator"
    parser_commandActuator = subparsers.add_parser("commandActuator", help="Force a command on the given actuator")
    parser_commandActuator.add_argument('command', help='Given command')
    parser_commandActuator.add_argument("-a", "--actuator", choices=["Led"], default="Led", help='Given actuator')
    parser_commandActuator.set_defaults(func=commandActuator)
    # "getAll"
    parser_getAll = subparsers.add_parser("getAll", help="Get all data from the given sensor")
    parser_getAll.add_argument('-s', "--sensor", choices=["Humidity"], default="Humidity", help='Given sensor')
    parser_getAll.set_defaults(func=getAll)
    # "getLatest"
    parser_getLatest = subparsers.add_parser("getLatest", help="Get latest data from the given sensor")
    parser_getLatest.add_argument('-s', "--sensor", choices=["Humidity"], default="Humidity", help='Given sensor')
    parser_getLatest.set_defaults(func=getLatest)

    args = parser.parse_args()

    print(args)

    sensorToMonitor = args.sensor + "Sensor"
    actuatorToTrigger = args.actuator + "Actuator"

    if args.__contains__("func"):
        args.func(args)


def RainAtLocationInXHours(location, hours):
    # API Setup
    APIKEY = config["API"]['key']
    owm = OWM(APIKEY)
    mgr = owm.weather_manager()

    # On creer une variable contenant les previsions mise a jours toute les 3h
    three_h_forecaster = mgr.forecast_at_place(location, '3h')

    # on creer une variable temps qui contient le temps dans X heures
    inXHours = timestamps.now() + timedelta(hours=hours)

    # On recupere l'info sur la pluie
    rain = three_h_forecaster.will_be_rainy_at(inXHours)

    # On renvoie un booleen selon s'il va pleuvoir a cette lcation dans les x procchaines heures
    return rain


if __name__ == '__main__':
    getParameters()

    if (sensorToMonitor == "HumiditySensor"):
        humidityThreshold = humidityThreshold

    if (actuatorToTrigger == "LedActuator"):
        isLedOn = False

    createAE()
    api.run(host=monitorIP, port=monitorPort)
