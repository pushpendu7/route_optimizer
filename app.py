# app.py
import streamlit as st
import pandas as pd
import json
import os
from api_clients import get_static_map_image_url
from agents import PlannerAgent, OptimizerAgent, MonitorAgent, DispatcherAgent
from models import train_and_save_model
from datetime import datetime
import utils
import folium
from streamlit_folium import st_folium  # optional; but will use folium embed fallback

st.set_page_config(layout="wide", page_title="AI Logistics Route Optimizer")

# -------------------------
# Helper to load sample data
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

# -------------------------
# Simple authentication / role selection (demo mode)
st.sidebar.title("User Login")
role = st.sidebar.selectbox("Role", ["Delivery Agent", "Operator (Admin)"])
username = st.sidebar.text_input("Username", value = "demo_user")
if st.sidebar.button("Train sample model (optional)"):
    train_and_save_model()
    st.sidebar.success("Trained and saved travel_time_model.pkl")

st.title("AI Agent for Real-time Logistics Route Optimization")
st.markdown(
    """
    **Features included**
    - Multi-agent system (Planner, Optimizer, Monitor, Dispatcher)
    - Real API hooks (OpenWeatherMap, Mapbox, OpenRouteService) — configure API keys via environment variables
    - Streamlit UI for Admin & Delivery Agent
    - Route override and manual dispatch
    - Map visualization
    """
)

# -------------------------
# Shared controls
st.sidebar.header("Dispatcher Controls")
start_lat = st.sidebar.number_input("Depot Latitude", value = 28.6139, format="%.6f")
start_lon = st.sidebar.number_input("Depot Longitude", value = 77.2090, format="%.6f")
operator_instructions = st.sidebar.text_area("Operator Instructions", value = "Deliver high-priority first; avoid highways if heavy rain.")

# instantiate agents
planner = PlannerAgent()
optimizer = OptimizerAgent()
monitor = MonitorAgent(traffic_feed = traffic_feed, weather_feed = weather_feed)
dispatcher = DispatcherAgent()



# -------------------------
# ROLE: Operator (Admin)
if role == "Operator (Admin)":
    st.header("Operator / Admin Dashboard")
    col1, col2 = st.columns([2,1])
    with col1:
        st.subheader("Pending Deliveries")
        df = pd.DataFrame(deliveries)
        st.dataframe(df)
        
        st.subheader("Plan Generation")
        if st.button("Generate optimized plan now"):
            ordered_ids = planner.prioritize(deliveries, operator_instructions)
            # convert to list of delivery dicts in that order
            id_map = {d["id"]: d for d in deliveries}
            ordered_delivery_dicts = [id_map[i["id"]] for i in ordered_ids if i["id"] in id_map]
            plan = optimizer.compute_plan((start_lat, start_lon), ordered_delivery_dicts)
            st.session_state["current_plan"] = plan
            st.success("Plan generated and saved in session")
        if "current_plan" in st.session_state:
            st.subheader("Current Plan Summary")
            p = st.session_state["current_plan"]
            st.markdown("**Route Map**")
            utils.display_route_plan_streamlit(p)

            # Show map
        st.subheader("Manual Override")
        st.markdown("You can reorder delivery sequence by entering a comma-separated list of IDs (e.g. D002,D001,D003)")
        override_str = st.text_input("New order (comma separated)", key="override_str")
        if st.button("Apply Override"):
            if "current_plan" not in st.session_state:
                st.error("No plan in session to override")
            else:
                new_order = [s.strip() for s in override_str.split(",") if s.strip()]
                override = {"type":"reorder", "new_order": new_order}
                st.session_state["current_plan"] = dispatcher.apply_override(st.session_state["current_plan"], override)
                st.success("Override applied")
    with col2:
        st.subheader("Live Traffic Feed")
        # st.json(traffic_feed)
        # utils.display_dict_in_streamlit_nested(traffic_feed)
        utils.st.dataframe(utils.json_to_table(traffic_feed))
        st.subheader("Live Weather Feed")
        # st.json(weather_feed)
        # utils.display_dict_in_streamlit_nested(weather_feed)
        utils.st.dataframe(utils.json_to_table(weather_feed))

    st.markdown("---")
    st.subheader("Monitor & Auto-Reroute")
    events = monitor.evaluate()
    st.write("Detected events:", events)
    # display_dict_in_streamlit_nested(events)

    if events:
        if st.button("Auto replan (considering events)"):
            # simple behavior: bump any deliveries near event latlon or in high severity
            st.info("Replanning triggered by monitor events")
            # We just regenerate ordering with operator instructions + appended 'avoid' if needed
            ordered_ids = planner.prioritize(deliveries, operator_instructions + " Consider avoiding high congestion segments if possible.")
            id_map = {d["id"]: d for d in deliveries}
            ordered_delivery_dicts = [id_map[i["id"]] for i in ordered_ids if i["id"] in id_map]
            new_plan = optimizer.compute_plan((start_lat, start_lon), ordered_delivery_dicts)
            st.session_state["current_plan"] = new_plan
            st.success("Auto replan complete")

# -------------------------
# ROLE: Delivery Agent
else:
    st.header("Delivery Agent Dashboard")
    st.subheader("Assigned Route")
    if "current_plan" not in st.session_state:
        st.info("No plan yet — Operator must generate a plan.")
    else:
        plan = st.session_state["current_plan"]
        st.write("Sequence:")
        for idx, stop in enumerate(plan["stops"]):
            if stop.get("id") == "START":
                st.markdown(f"**{idx}. Depot** ({stop['lat']}, {stop['lon']})")
            else:
                st.markdown(f"**{idx}. {stop['id']}** — {stop.get('address','')}")
                # arrival ETA if available
                if idx-1 < len(plan.get("etas",[])):
                    st.caption(f"ETA: {plan['etas'][idx-1]}")
        st.subheader("Map View")
        try:
            m = folium.Map(location=[start_lat, start_lon], zoom_start=11)
            folium.Marker([start_lat, start_lon], tooltip="Depot", icon=folium.Icon(color="green")).add_to(m)
            for stop in plan["stops"]:
                if stop.get("id") == "START": continue
                folium.Marker([stop["lat"], stop["lon"]], tooltip=f"{stop['id']}").add_to(m)
            st_folium(m, width=700, height=500)
        except Exception as e:
            st.error("Map rendering requires streamlit-folium or folium installed.")
        st.subheader("Agent Actions")
        if st.button("Request Reroute (send reason)"):
            st.success("Reroute request submitted to operator (demo)")
        if st.button("Mark current stop as delivered"):
            st.success("Marked as delivered (demo)")

st.sidebar.markdown("---")
st.sidebar.caption("Configure API keys in environment variables: OPENWEATHER_API_KEY, MAPBOX_TOKEN, ORS_API_KEY, OPENAI_API_KEY")
