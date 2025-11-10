import math
import json
import folium
import random
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st
from folium import plugins
from datetime import datetime
from streamlit_folium import st_folium


def display_dict_in_streamlit_nested(data_dict: dict, indent: int = 2):
    """Display a dictionary (including nested ones) in a nicely formatted way in Streamlit."""

    if not data_dict:
        st.write("The dictionary is empty.")
        return

    format_list = ["Json", "Dict", "YAML"]
    format = st.radio("Format", horizontal = True, options = format_list, key = data_dict.get(next(iter(data_dict))))

    if format == format_list[0]:
        st.write(data_dict)

    if format == format_list[1]:
        max_key_length = max(len(str(key)) for key in data_dict.keys())
        padding = max_key_length + 2

        output_lines = []
        for key, value in data_dict.items():
            display_value = str(value)
            formatted_line = f"{str(key).replace('_', ' ').title():<{padding}}: {display_value}"
            output_lines.append(formatted_line)
        content_to_display = "\n".join(output_lines)
        st.code(content_to_display, language = "yaml", width = "content")

    if format == format_list[2]:
        def format_nested(data, level=0):
            """Recursively format nested dicts and lists into aligned text with indentation."""
            lines = []
            indent_space = "    " * level  # 4 spaces per indent level

            if isinstance(data, dict):
                # Calculate padding for alignment at this level
                max_key_len = max((len(str(k)) for k in data.keys()), default=0)
                padding = max_key_len + 2
                for key, value in data.items():
                    display_key = str(key).replace("_", " ").title()
                    if isinstance(value, (dict, list)):
                        lines.append(f"{indent_space}{display_key}:")
                        lines.extend(format_nested(value, level + 1))
                    else:
                        lines.append(f"{indent_space}{display_key:<{padding}}: {value}")
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    if isinstance(item, (dict, list)):
                        lines.append(f"{indent_space}- Item {i+1}:")
                        lines.extend(format_nested(item, level + 1))
                    else:
                        lines.append(f"{indent_space}- {item}")
            else:
                lines.append(f"{indent_space}{data}")

            return lines

        formatted_text = "\n".join(format_nested(data_dict))
        st.code(formatted_text, language = "yaml", width = "content")


def display_route_plan_streamlit(route_data: dict):
    """
    Displays a delivery route plan using Folium inside Streamlit with numbered,
    priority-colored markers and connecting route lines.
    """

    try:
        if not route_data or "stops" not in route_data:
            st.error("Invalid route data — missing 'stops' key.")
            return

        stops = route_data["stops"]
        segment_minutes = route_data.get("estimated_segment_minutes", [])
        etas = route_data.get("etas", [])
        route_summary = route_data.get("route_summary", {})

        # Calculate map center
        start_lat, start_lon = stops[0]["lat"], stops[0]["lon"]

        # Priority → color map
        color_map = {"high": "red", "medium": "orange", "low": "green"}

        # Create Folium map
        m = folium.Map(location=[start_lat, start_lon], zoom_start=11, control_scale=True)

        # Add depot/start marker
        folium.Marker(
            [start_lat, start_lon],
            tooltip="Start Point (Depot)",
            icon = folium.Icon(color = "blue", icon = "warehouse", prefix = "fa"),
        ).add_to(m)

        # List for route polyline
        route_coords = [(start_lat, start_lon)]

        # Add delivery stops
        for i, stop in enumerate(stops):
            if stop.get("id") == "START":
                continue

            lat, lon = stop["lat"], stop["lon"]
            route_coords.append((lat, lon))

            # Marker color by priority
            priority = stop.get("priority", "low").lower()
            color = color_map.get(priority, "gray")

            # ETA handling
            if i < len(etas):
                try:
                    eta_time = datetime.fromisoformat(etas[i])
                    eta_str = eta_time.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    eta_str = etas[i]
            else:
                eta_str = "N/A"

            travel_time = (
                f"{segment_minutes[i-1]:.1f} min" if i > 0 and i-1 < len(segment_minutes) else "N/A"
            )

            # Marker label (S, 1, 2, 3, etc.)
            marker_label = f"S" if stop["id"].upper() == "START" else f"{i}"

            popup_html = f"""
            <b>Stop ID:</b> {stop['id']}<br>
            <b>Address:</b> {stop.get('address', 'N/A')}<br>
            <b>Priority:</b> {priority.capitalize()}<br>
            <b>Package Size:</b> {stop.get('package_size', 'N/A').capitalize()}<br>
            <b>ETA:</b> {eta_str}<br>
            <b>Travel Time:</b> {travel_time}
            """

            folium.Marker(
                [lat, lon],
                tooltip=f"Stop {i}: {stop.get('address', 'N/A')}",
                popup=folium.Popup(popup_html, max_width=300),
                # icon=html_marker,
                icon=folium.Icon(color = color, icon = marker_label, prefix = "fa"),
            ).add_to(m)

        # Add route line connecting all stops
        folium.PolyLine(
            route_coords,
            color="blue",
            weight=4,
            opacity=0.7,
            tooltip="Planned Route Path",
        ).add_to(m)

        # Add total route summary
        distance_km = route_summary.get("distance_m", 0) / 1000
        duration_min = route_summary.get("duration_s", 0) / 60
        st.markdown(f"**Total Distance:** {distance_km:.2f} km  |  **Estimated Duration:** {duration_min:.1f} minutes")

        # Render map
        st_data = st_folium(m, width=700, height=500)
        st.write(":grey[Priorities:]  High = 🔴 Red | Medium = 🟠 Orange | Low = 🟢 Green")

    except Exception as e:
        st.error(f"Map rendering failed: {e}")
        st.info("Make sure `streamlit-folium` and `folium` are installed.")


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Compute Haversine distance between two lat/lon points in kilometers.
    """
    R = 6371  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def assign_nearest_depot_to_clusters(clusters, depots):
    """
    Assigns nearest depot to each delivery cluster based on centroid location.

    Parameters:
        clusters (dict): {cluster_id: [delivery_dicts]} from HDBSCAN output
        depots (list[dict]): [{"name": "Depot A", "lat": 22.57, "lon": 88.36}, ...]

    Returns:
        list[dict]: cluster assignment info (cluster_id, centroid, depot, distance_km)
    """

    cluster_assignments = []

    for cluster_id, deliveries in clusters.items():
        # Skip outliers
        if cluster_id == "Outlier" or len(deliveries) == 0:
            continue

        # --- Compute centroid of cluster ---
        avg_lat = sum(d["lat"] for d in deliveries) / len(deliveries)
        avg_lon = sum(d["lon"] for d in deliveries) / len(deliveries)

        # --- Find nearest depot ---
        nearest_depot = None
        min_distance = float("inf")

        for idx, (dep_lat, dep_lon) in enumerate(depots):
            dist = haversine_distance(avg_lat, avg_lon, dep_lat, dep_lon)
            if dist < min_distance:
                min_distance = dist
                nearest_depot = (dep_lat, dep_lon)
                depot_index = idx + 1  # for labeling (Depot 1, Depot 2, etc.)

        cluster_assignments.append({
            "cluster_id": cluster_id,
            "centroid_lat": avg_lat,
            "centroid_lon": avg_lon,
            "nearest_depot_id": f"Depot_{depot_index}",
            "depot_lat": nearest_depot[0],
            "depot_lon": nearest_depot[1],
            "distance_km": round(min_distance, 2)
        })

    return cluster_assignments



def get_traffic_data(json_data):
    """
    Convert the traffic segment JSON data into a tabular (DataFrame) format.
    
    Args:
        json_data (dict or str): JSON data as a dictionary or JSON string.
    
    Returns:
        pd.DataFrame: A DataFrame with structured tabular data.
    """
    # Parse if input is a JSON string
    if isinstance(json_data, str):
        json_data = json.loads(json_data)
    
    # Extract timestamp
    timestamp = json_data.get("timestamp")
    
    # Extract and flatten segment data
    records = []
    for seg in json_data.get("segments", []):
        record = {
            "timestamp": timestamp,
            "segment_id": seg.get("segment_id"),
            "start_lat": seg["start"][0],
            "start_lon": seg["start"][1],
            "end_lat": seg["end"][0],
            "end_lon": seg["end"][1],
            "congestion_level": seg.get("congestion_level"),
            "avg_speed_kmph": seg.get("avg_speed_kmph")
        }
        records.append(record)
    
    # Convert to DataFrame
    df = pd.DataFrame(records)
    return df


def get_weather_data(data):
    """
    Converts a weather JSON structure to a pandas DataFrame.

    Example input:
    {
        "timestamp": "2025-11-04T06:00:00+05:31",
        "locations": [
            {"lat": 28.6315, "lon": 77.2167, "temp_c": 22, "conditions": "thunderstorm"},
            {"lat": 28.5703, "lon": 77.324, "temp_c": 23, "conditions": "clouds"},
            {"lat": 28.4936, "lon": 77.0896, "temp_c": 21, "conditions": "rain"},
            {"lat": 28.5682, "lon": 77.2378, "temp_c": 22, "conditions": "clear"}
        ]
    }
    """
    # Convert list of locations to DataFrame
    df = pd.DataFrame(data["locations"])

    # Add timestamp column
    df["timestamp"] = data["timestamp"]

    return df

def visualize_clusters_on_map(coordinates, cluster_labels):
    """
    Visualize clustered delivery points on a Folium map with color-coded markers.
    """
    # Center map around mean coordinates
    avg_lat = np.mean([lat for lat, lon in coordinates])
    avg_lon = np.mean([lon for lat, lon in coordinates])
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start = 11)

    # Assign random colors to clusters
    unique_labels = set(cluster_labels)
    colors = {
        label: f"#{random.randint(0, 0xFFFFFF):06x}"
        for label in unique_labels if label != -1
    }
    colors[-1] = "black"  # noise points

    # Add points to map
    for (lat, lon), label in zip(coordinates, cluster_labels):
        color = colors.get(label, "gray")
        
        folium.CircleMarker(
            location = [lat, lon],
            radius = 6,
            color = color,
            fill = True,
            fill_opacity = 0.8,
            tooltip = f"Zone {label}" if label != -1 else "Noise"
        ).add_to(m)

        # folium.Marker(
        #         [lat, lon],
        #         # tooltip = f"Zone {label}" if label != -1 else "Noise",
        #         popup = folium.Popup(label, max_width=300),
        #         # icon=folium.Icon(color = color)
        #     ).add_to(m)

    return m
