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
    "North Kolkata" : {
        "center": [22.6100, 88.3900],  # near Shyambazar, Dum Dum
        "bounds": {
                    "min_lat": 22.5800,
                    "max_lat": 22.6600,
                    "min_lon": 88.3400,
                    "max_lon": 88.4200,
                },
        "depots" : [(22.6312, 88.3518), (22.6544, 88.3915)]
    },

    # Define South Kolkata coordinates and area
    "South Kolkata" : {
        "center": [22.4950, 88.3650],  # near Tollygunge, Jadavpur
        "bounds": {
                    "min_lat": 22.4500,
                    "max_lat": 22.5200,
                    "min_lon": 88.3000,
                    "max_lon": 88.4200,
                },
        "depots" : [(22.4883, 88.3790), (22.5012, 88.4123)]
    }
}
