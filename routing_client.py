# routing_client.py
import os
import requests
from math import radians, cos, sin, asin, sqrt

ORS_API_KEY = os.getenv("ORS_API_KEY")  # optional: https://openrouteservice.org/

def haversine_km(lat1, lon1, lat2, lon2):
    # returns km
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2*asin(sqrt(a))
    r = 6371
    return c * r

def route_between_points(points):
    """
    points: list of (lon,lat) pairs in order
    Returns: dict with distance_m, duration_s, geometry (encoded or list)
    If ORS API key is available, use it. Otherwise, produce naive estimate using haversine + speeds.
    """
    if ORS_API_KEY:
        url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
        headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
        coords = [[p[0], p[1]] for p in points]
        resp = requests.post(url, json={"coordinates": coords}, headers=headers, timeout=20)
        resp.raise_for_status()
        j = resp.json()
        props = j["features"][0]["properties"]["summary"]
        return {"distance_m": props["distance"], "duration_s": props["duration"], "geometry": j["features"][0]["geometry"]}
    # Fallback: naïve sum of haversine distances and assume average speed 30 km/h
    total_km = 0
    for i in range(len(points)-1):
        total_km += haversine_km(points[i][1], points[i][0], points[i+1][1], points[i+1][0])
    avg_speed_kmph = 30
    duration_hours = total_km / avg_speed_kmph if avg_speed_kmph > 0 else 0
    return {"distance_m": total_km*1000, "duration_s": duration_hours*3600, "geometry": None}
