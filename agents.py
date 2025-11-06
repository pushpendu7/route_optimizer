import os
import time
import re
import random
import config
import json
from datetime import datetime, timedelta
from api_clients import get_weather_for_point
from routing_client import route_between_points
from models import load_model, train_and_save_model
import numpy as np
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
load_dotenv()


llm = init_chat_model(model = os.getenv("GROQ_MODEL_NAME"), model_provider = "groq")
# llm = init_chat_model(model = os.getenv("GEMINI_MODEL_NAME"), model_provider = "google_genai")

class PlannerAgent:
    """
    Uses LLM to interpret constraints and produce a prioritized order for deliveries.
    """
    def __init__(self, model="gpt-4o"):
        self.model = model

    def prioritize(self, deliveries, operator_instructions=""):
        """
        deliveries: list of dicts with keys id, priority, address, lat, lon
        operator_instructions: string with additional constraints
        Returns: ordered list of delivery ids
        """
        # Build a short prompt with deliveries summary
        prompt = "You are an operations planner. Rank deliveries with ids and reasons based on priority, location proximity and operator instructions.\n"
        prompt += f"Operator instructions: {operator_instructions}\n\nDeliveries:\n"
        for d in deliveries:
            prompt += f"- id:{d['id']}, priority:{d.get('priority','medium')}, lat:{d['lat']}, lon:{d['lon']}, package_size:{d.get('package_size','medium')}\n"
        prompt += "\nReturn a JSON array of ids in preferred visit order."
        try:
            print("Invoking LLM")
            resp = llm.invoke([{"role":"user","content":prompt}])
            print(f"Response Generated: {str(resp.content)}")
            text = str(resp.content).strip()
            # text = str(resp["content"]).strip()
            # attempt to parse json out of text
            m = re.search(r'(\[.*\])', text, re.S)
            if m:
                print("creating ordered json")
                ordered = json.loads(m.group(1))
                print("Completed ordering")
            else:
                # fallback: split by common separators
                print("Fallback: split by common separators")
                ordered = [tok.strip().strip('"').strip("'") for tok in re.split(r'[,\\n]+', text) if tok.strip()]
                print("Completed ordering")
            print(f"LLM ({os.getenv('GROQ_MODEL_NAME')}) suggestion: {ordered}")
            return ordered
        except Exception as e:
            # fallback: simple sort by priority mapping and id
            print(str(e))
            priority_map = {"high": 0, "medium": 1, "low": 2}
            ordered_delivery = sorted(deliveries, key=lambda x: (priority_map.get(x.get("priority","medium"),1), x["id"]))
            ordered = [i['id'] for i in ordered_delivery]
            print(f"Fallback sort based on Priority: {ordered}")
            return ordered

class OptimizerAgent:
    """
    Generates route plans using routing_client; uses travel-time model if present to refine durations.
    """
    def __init__(self, travel_time_model_path="travel_time_model.pkl"):
        self.model = None
        if os.path.exists(travel_time_model_path):
            try:
                self.model = load_model(travel_time_model_path)
            except:
                self.model = None

    def compute_plan(self, start_point, ordered_deliveries):
        """
        start_point: (lat, lon)
        ordered_deliveries: list of delivery dicts in visit order
        returns plan dict with sequenced stops, route summary (distance, duration), estimated arrival times
        """
        points = [(start_point[1], start_point[0])]  # (lon,lat) first
        for d in ordered_deliveries:
            points.append((d["lon"], d["lat"]))
        route = route_between_points(points)
        # If we have trained model, compute refined durations segment-wise
        est_segment_minutes = []
        if self.model:
            for i in range(len(points)-1):
                dist_km = route_distance_segment(points[i], points[i+1])
                congestion = 0.4  # placeholder; ideally from traffic feed
                precip = 0.0
                X = np.array([[dist_km, congestion, precip]])
                est = float(self.model.predict(X)[0])
                est_segment_minutes.append(est)
        else:
            # coarse split of total duration equally
            if route["duration_s"]:
                per = route["duration_s"] / (len(points)-1)
                est_segment_minutes = [per/60.0]*(len(points)-1)
        # Build ETA list
        now = datetime.now()
        eta_list = []
        cur = now
        for idx, segmin in enumerate(est_segment_minutes):
            cur = cur + timedelta(minutes=segmin)
            eta_list.append(cur.isoformat())
        plan = {
            "stops": [{"id":"START","lat":start_point[0],"lon":start_point[1]}] + ordered_deliveries,
            "route_summary": route,
            "estimated_segment_minutes": est_segment_minutes,
            "etas": eta_list
        }
        return plan

def route_distance_segment(p1, p2):
    # p1/p2: (lon,lat)
    from routing_client import haversine_km
    return haversine_km(p1[1], p1[0], p2[1], p2[0])

class MonitorAgent:
    """
    Polls weather/traffic feeds and raises alerts for the optimizer to replan.
    For demo: it reads from sample JSON (or from API clients).
    """
    def __init__(self, traffic_feed=None, weather_feed=None):
        self.traffic_feed = traffic_feed
        self.weather_feed = weather_feed

    def evaluate(self):
        """
        Return a list of events that may trigger reroute: e.g., heavy congestion on a segment or heavy rain.
        """
        events = []
        # simple heuristics from provided feed dicts
        if self.traffic_feed:
            for s in self.traffic_feed.get("segments",[]):
                if s["congestion_level"] > 0.75:
                    events.append({"type":"traffic", "segment": s["segment_id"], "severity":"high"})
        if self.weather_feed:
            for loc in self.weather_feed.get("locations", []):
                if "rain" in loc.get("conditions","").lower():
                    events.append({"type":"weather", "lat":loc["lat"], "lon":loc["lon"], "severity":"medium"})
        return events


class DispatcherAgent:
    """
    Applies manual overrides and finalizes dispatch decisions.
    """
    def __init__(self):
        self.overrides = []

    def apply_override(self, plan, override):
        """
        override: dict with type 'reorder' or 'skip' or 'insert' and relevant data
        Example: {"type":"reorder","new_order":["D002","D001","D003"]}
        """
        self.overrides.append(override)
        if override["type"] == "reorder":
            # reorder plan stops accordingly
            id_to_stop = {s['id']: s for s in plan['stops'] if s.get('id')!='START'}
            new_stops = [id_to_stop[i] for i in override["new_order"] if i in id_to_stop]
            plan['stops'] = [plan['stops'][0]] + new_stops
        elif override["type"] == "skip":
            # remove a stop
            plan['stops'] = [s for s in plan['stops'] if s.get('id') != override["id"]]
        return plan


class DataGeneratorAgent:
    def __init__(self):
        self.locations = config.locations

    def generate_orders(self, num_orders, location):
        """
        Generate realistic delivery orders using an LLM within given mapbox coordinates.
        """
        bounds = self.locations[location]["bounds"]
        # Step 1: Generate random lat/lon pairs within bounds
        coords = [
            {
                "lat": round(random.uniform(bounds["min_lat"], bounds["max_lat"]), 6),
                "lon": round(random.uniform(bounds["min_lon"], bounds["max_lon"]), 6)
            }
            for _ in range(num_orders)
        ]

        # Step 2: Construct a system prompt for LLM
        system_prompt = (
            "You are a logistics data generator."
            f"Generate delivery order JSON objects for a courier company in {location}"
            "Each order should include: id, customer_name, address, lat, lon, priority, package_size, fragile."
            f"Use realistic Bengali or Indian names and real street/locality-style addresses in {location}."
            "Priorities should be 'high', 'medium', or 'low'. Package sizes: 'small', 'medium', 'large'."
            "Fragile is true or false. "
            "Return JSON only as string."
        )

        # Step 3: Combine lat/lon into the prompt
        user_prompt = f"Generate {num_orders} delivery orders for these coordinates:\n{json.dumps(coords, indent = 2)}"

        # Step 4: Call the LLM
        response = llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}],
        )

        # Step 5: Parse and return structured JSON
        try:
            orders = json.loads(response.content)
            with open(config.DELIVERIES_FILE, 'w') as file:
                json.dump(orders, file, indent=4)

        except json.JSONDecodeError:
            print("⚠️ Could not parse JSON. Raw LLM output:")
            print(response.content)
            return []
        
        # return orders

