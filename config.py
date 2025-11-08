import os
import json

DATA_DIR = "data"
DELIVERIES_FILE = os.path.join(DATA_DIR, "deliveries.json")
TRAFFIC_FILE = os.path.join(DATA_DIR, "sample_traffic.json")
WEATHER_FILE = os.path.join(DATA_DIR, "sample_weather.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

deliveries = load_json(DELIVERIES_FILE)
traffic_feed = load_json(TRAFFIC_FILE)
weather_feed = load_json(WEATHER_FILE)



locations = {
    "Kolkata" : {
        "center": [22.5726, 88.3639],
        "bounds": {
                    "min_lat": 22.6400,
                    "max_lat": 22.5000,
                    "min_lon": 88.3400,
                    "max_lon": 88.4500,
                },
        "depots" : [(22.5048, 88.3475), (22.5832, 88.4325)]
    },
}
