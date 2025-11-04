# api_clients.py
import os
import requests
from dotenv import load_dotenv
load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")  # get from https://openweathermap.org/
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")  # get from https://www.mapbox.com/
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # for LLM-based agents (optional)

def get_weather_for_point(lat, lon):
    """
    Fetch current weather from OpenWeatherMap
    """
    if not OPENWEATHER_API_KEY:
        raise RuntimeError("OPENWEATHER_API_KEY not set in environment")
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "units": "metric", "appid": OPENWEATHER_API_KEY}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    # return minimal useful fields
    return {
        "temp_c": data["main"]["temp"],
        "conditions": data["weather"][0]["description"],
        "wind_mps": data["wind"].get("speed", None),
        "raw": data
    }

def get_static_map_image_url(lat, lon, zoom=12, width=800, height=600):
    """
    Returns a Mapbox Static Image URL for simple embedding.
    """
    if not MAPBOX_TOKEN:
        # return blank or throw — but provide an alternative: OpenStreetMap static tile
        return None
    # Mapbox Static API
    return f"https://api.mapbox.com/styles/v1/mapbox/streets-v11/static/pin-s+ff0000({lon},{lat})/{lon},{lat},{zoom}/{width}x{height}?access_token={MAPBOX_TOKEN}"

def geocode_address(address):
    """
    Very simple geocoder via Mapbox (or fallback to Nominatim if no token).
    """
    if MAPBOX_TOKEN:
        url = "https://api.mapbox.com/geocoding/v5/mapbox.places/{}.json".format(requests.utils.requote_uri(address))
        params = {"access_token": MAPBOX_TOKEN, "limit": 1}
        r = requests.get(url, params=params, timeout=10); r.raise_for_status()
        j = r.json()
        if j.get("features"):
            lon, lat = j["features"][0]["center"]
            return {"lat": lat, "lon": lon, "place_name": j["features"][0]["place_name"]}
    # fallback to Nominatim (OpenStreetMap) — polite use only
    url = "https://nominatim.openstreetmap.org/search"
    resp = requests.get(url, params={"q": address, "format": "json", "limit": 1}, headers={"User-Agent":"ai-logistics-app"}, timeout=10)
    resp.raise_for_status()
    j = resp.json()
    if j:
        return {"lat": float(j[0]["lat"]), "lon": float(j[0]["lon"]), "place_name": j[0]["display_name"]}
    return None
