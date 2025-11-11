import os
import json
from pathlib import Path

# Home Directory
HOME_DIR = Path(Path(__file__).resolve()).parent.parent

# Subdirectories
DB_DIR = Path(HOME_DIR, "db")
MODEL_DIR = Path(HOME_DIR, "models")
ASSETS_DIR = Path(HOME_DIR, "assets")
CONFIG_DIR = Path(HOME_DIR, "config")
PAGES_DIR = Path(HOME_DIR, "pages")
LOG_DIR = Path(HOME_DIR, "logs")
CSS_DIR = Path(HOME_DIR, "css")
DATA_DIR = Path(HOME_DIR, "data")

# Output Directories
OUTPUT_DIR = Path(DATA_DIR, "output")

DELIVERIES_FILE = os.path.join(DATA_DIR, "deliveries.json")
TRAFFIC_FILE = os.path.join(DATA_DIR, "sample_traffic.json")
WEATHER_FILE = os.path.join(DATA_DIR, "sample_weather.json")

locations = {
    "Kolkata" : {
        "bounds": {
                    "min_lat": 22.6400,
                    "max_lat": 22.5000,
                    "min_lon": 88.3400,
                    "max_lon": 88.4500,
                },
        "depots" : [(22.5048, 88.3475), (22.5832, 88.4325)]
    },

    "Delhi": {
        "bounds": {
            "min_lat": 28.4000,
            "max_lat": 28.8800,
            "min_lon": 76.8400,
            "max_lon": 77.3500,
        },
        "depots": [(28.6139, 77.2090), (28.5465, 77.2732)]
    },

    "Mumbai": {
        "bounds": {
            "min_lat": 18.8800,
            "max_lat": 19.2800,
            "min_lon": 72.7700,
            "max_lon": 72.9900,
        },
        "depots": [(19.0760, 72.8777), (19.2288, 72.8567)]
    },

    "Pune": {
        "bounds": {
            "min_lat": 18.4200,
            "max_lat": 18.6200,
            "min_lon": 73.7500,
            "max_lon": 73.9800,
        },
        "depots": [(18.5204, 73.8567), (18.5890, 73.9130)]
    },

    "Bangalore": {
        "bounds": {
            "min_lat": 12.8500,
            "max_lat": 13.1500,
            "min_lon": 77.4500,
            "max_lon": 77.7500,
        },
        "depots": [(12.9716, 77.5946), (13.0050, 77.6200)]
    },

    "Hyderabad": {
        "bounds": {
            "min_lat": 17.2500,
            "max_lat": 17.5500,
            "min_lon": 78.3000,
            "max_lon": 78.6000,
        },
        "depots": [(17.3850, 78.4867), (17.4500, 78.5500)]
    },
}

USERS = {
            "Dispatch Operator (Admin)" : "admin", 
            "Delivery Agent" : "user",
        }

MAIN_APPS = [
    {"name": "OrderMap",
     "description": "Data-rich interface for orders and coordinates",
     "page": "ordermap.py",
     "page_icon": ":material/orders:",
     "image_icon": "ordermap.png",
     "access_privilege_role": ["admin"],
    },
    {"name": "RouteBoard",
     "description": "Dashboard combining orders and map routes",
     "page": "routeboard.py",
     "page_icon": ":material/route:",
     "image_icon": "routeboard.png",
     "access_privilege_role": ["user"],
    },
    {"name": "EventWatch",
     "description": "Full-scope alert monitoring system",
     "page": "eventwatch.py",
     "page_icon": ":material/earthquake:",
     "image_icon": "eventwatch.png",
     "access_privilege_role": ["admin"],
    },
    {"name": "TrackFleet",
     "description": "For tracking field agents or delivery fleets",
     "page": "trackfleet.py",
     "page_icon": ":material/track_changes:",
     "image_icon": "trackfleet.png",
     "access_privilege_role": ["admin"],
    },
    {"name": "AgentAssist",
     "description": "Operator control and support dashboard",
     "page": "agentassist.py",
     "page_icon": ":material/support_agent:",
     "image_icon": "agentassist.png",
     "access_privilege_role": ["user"],
    },
]