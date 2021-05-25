import configparser

from pyowm import OWM
import json
from pyowm.utils import timestamps
from datetime import timedelta
from pathlib import Path

#/////////////// Parameters /////////////////
config = configparser.ConfigParser()
path = Path(__file__).parent / "default.json"
with open(path, 'r') as f:
    config = json.load(f)

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

    return rain


if __name__ == '__main__':

    # preuve que ca marche
    print("pluie a marseille dans 8 h ?" + str(RainAtLocationInXHours(config['location']['city']+','+config['location']['country'], 8)))
    print("pluie a londre dans 8 h ?" + str(RainAtLocationInXHours('London,GB', 8)))
    print("pluie a londre dans 8 h ?" + str(RainAtLocationInXHours('London,GB', 8)))
