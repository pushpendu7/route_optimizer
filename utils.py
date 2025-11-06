import json
import streamlit as st
import pandas as pd
from datetime import datetime
import pydeck as pdk
import requests
import folium
from folium import plugins
from streamlit_folium import st_folium


def display_dict_in_streamlit_nested(data_dict: dict, indent: int = 0):
    """Display a dictionary (including nested ones) in a nicely formatted way in Streamlit."""

    if not data_dict:
        st.write("The dictionary is empty.")
        return

    format_list = ["Json", "Dict", "YAML"]
    format = st.radio("Format", horizontal = True, options = format_list, index = 2, key = data_dict.get(next(iter(data_dict))))

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

def display_route_plan(route_data: dict):
    """
    Displays a delivery route plan in an intuitive, human-friendly format in Streamlit.
    """

    if not route_data or "stops" not in route_data:
        st.warning("No valid route data provided.")
        return

    stops = route_data["stops"]
    route_summary = route_data.get("route_summary", {})
    segment_minutes = route_data.get("estimated_segment_minutes", [])
    etas = route_data.get("etas", [])

    # --- HEADER ---
    st.subheader("🚚 Delivery Route Plan")
    st.markdown("---")

    # --- ROUTE SUMMARY ---
    st.markdown("### 🗺️ Route Summary")
    distance_km = route_summary.get("distance_m", 0) / 1000
    duration_min = route_summary.get("duration_s", 0) / 60
    st.write(f"**Total Distance:** {distance_km:.2f} km")
    st.write(f"**Estimated Duration:** {duration_min:.1f} minutes")

    st.markdown("---")
    st.markdown("### 📍 Stop Details")

    # --- STOP-BY-STOP DETAILS ---
    for i, stop in enumerate(stops):
        stop_num = "Start Point" if stop["id"].upper() == "START" else f"Stop {i}"
        st.markdown(f"#### 🧭 {stop_num}: {stop.get('id')}")
        
        if stop.get("address"):
            st.write(f"**Address:** {stop['address']}")
        st.write(f"**Latitude:** {stop['lat']}, **Longitude:** {stop['lon']}")

        if "priority" in stop:
            st.write(f"**Priority:** {stop['priority'].capitalize()}")
        if "package_size" in stop:
            st.write(f"**Package Size:** {stop['package_size'].capitalize()}")

        # ETA (if available)
        if i < len(etas):
            try:
                eta_time = datetime.fromisoformat(etas[i])
                st.write(f"**ETA:** {eta_time.strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception:
                st.write(f"**ETA:** {etas[i]}")

        # Segment travel info (from previous stop)
        if i > 0 and i - 1 < len(segment_minutes):
            travel_time = segment_minutes[i - 1]
            st.write(f"**Travel Time from Previous Stop:** {travel_time:.1f} minutes")

        st.markdown("---")

    # --- TIMELINE VIEW ---
    st.markdown("### 🕒 Timeline Overview")
    if etas:
        try:
            for idx, eta in enumerate(etas):
                eta_dt = datetime.fromisoformat(eta)
                stop_id = stops[idx].get("id")
                addr = stops[idx].get("address", "N/A")
                st.text(f"{eta_dt.strftime('%H:%M:%S')} → {stop_id} ({addr})")
        except Exception:
            st.json(etas)

    st.success("✅ Route plan displayed successfully.")



def display_route_plan_visual(route_data: dict):
    """
    Displays a delivery route plan with an intuitive summary, stop details, and interactive map visualization in Streamlit.
    """

    if not route_data or "stops" not in route_data:
        st.warning("No valid route data provided.")
        return

    stops = route_data["stops"]
    route_summary = route_data.get("route_summary", {})
    segment_minutes = route_data.get("estimated_segment_minutes", [])
    etas = route_data.get("etas", [])

    # --- HEADER ---
    st.subheader("🚚 Delivery Route Plan")
    st.markdown("---")

    # --- ROUTE SUMMARY ---
    st.markdown("### 🗺️ Route Summary")
    distance_km = route_summary.get("distance_m", 0) / 1000
    duration_min = route_summary.get("duration_s", 0) / 60
    st.write(f"**Total Distance:** {distance_km:.2f} km")
    st.write(f"**Estimated Duration:** {duration_min:.1f} minutes")
    st.markdown("---")

    # --- STOP DETAILS ---
    st.markdown("### 📍 Stop Details")
    stop_records = []
    for i, stop in enumerate(stops):
        stop_num = "Start Point" if stop["id"].upper() == "START" else f"Stop {i}"
        st.markdown(f"#### 🧭 {stop_num}: {stop.get('id')}")
        
        if stop.get("address"):
            st.write(f"**Address:** {stop['address']}")
        st.write(f"**Latitude:** {stop['lat']}, **Longitude:** {stop['lon']}")

        if "priority" in stop:
            st.write(f"**Priority:** {stop['priority'].capitalize()}")
        if "package_size" in stop:
            st.write(f"**Package Size:** {stop['package_size'].capitalize()}")

        if i < len(etas):
            try:
                eta_time = datetime.fromisoformat(etas[i])
                eta_str = eta_time.strftime('%Y-%m-%d %H:%M:%S')
                st.write(f"**ETA:** {eta_str}")
            except Exception:
                st.write(f"**ETA:** {etas[i]}")
        else:
            eta_str = "N/A"

        # Segment travel info (from previous stop)
        if i > 0 and i - 1 < len(segment_minutes):
            travel_time = segment_minutes[i - 1]
            st.write(f"**Travel Time from Previous Stop:** {travel_time:.1f} minutes")

        st.markdown("---")

        stop_records.append({
            "id": stop.get("id"),
            "address": stop.get("address", ""),
            "lat": stop.get("lat"),
            "lon": stop.get("lon"),
            "priority": stop.get("priority", ""),
            "package_size": stop.get("package_size", ""),
            "eta": eta_str
        })

    # --- TIMELINE OVERVIEW ---
    st.markdown("### 🕒 Timeline Overview")
    for s in stop_records:
        st.text(f"{s['eta']} → {s['id']} ({s.get('address', 'N/A')})")

    st.markdown("---")

    # --- MAP VISUALIZATION ---
    st.markdown("### 🗺️ Route Map")
    df = pd.DataFrame(stop_records)

    # Define layer for markers
    icon_data = {
        "url": "https://cdn-icons-png.flaticon.com/512/684/684908.png",
        "width": 128,
        "height": 128,
        "anchorY": 128,
    }

    df["icon_data"] = [icon_data] * len(df)

    icon_layer = pdk.Layer(
        "IconLayer",
        data=df,
        get_icon="icon_data",
        get_position=["lon", "lat"],
        get_size=3,
        pickable=True,
    )

    # Draw lines between consecutive stops
    route_lines = []
    for i in range(len(df) - 1):
        route_lines.append({
            "from": [df.iloc[i]["lon"], df.iloc[i]["lat"]],
            "to": [df.iloc[i + 1]["lon"], df.iloc[i + 1]["lat"]],
        })

    line_layer = pdk.Layer(
        "LineLayer",
        data=route_lines,
        get_source_position="from",
        get_target_position="to",
        get_color=[255, 100, 0],
        get_width=4,
    )

    # Define map view centered around first stop
    midpoint = (df["lat"].mean(), df["lon"].mean())
    view_state = pdk.ViewState(latitude=midpoint[0], longitude=midpoint[1], zoom=10)

    r = pdk.Deck(
        layers=[line_layer, icon_layer],
        initial_view_state=view_state,
        tooltip={
            "text": "Stop: {id}\nETA: {eta}\nPriority: {priority}\nPackage: {package_size}"
        },
    )

    st.pydeck_chart(r)
    st.success("✅ Route plan displayed successfully with map.")



def display_route_plan_map(route_data: dict):
    """
    Displays a delivery route plan with realistic route geometry (via OSRM),
    stop details, and interactive map visualization in Streamlit.
    """

    if not route_data or "stops" not in route_data:
        st.warning("No valid route data provided.")
        return

    stops = route_data["stops"]
    route_summary = route_data.get("route_summary", {})
    segment_minutes = route_data.get("estimated_segment_minutes", [])
    etas = route_data.get("etas", [])

    # --- HEADER ---
    st.subheader("🚚 Delivery Route Plan")
    st.markdown("---")

    # --- ROUTE SUMMARY ---
    st.markdown("### 🗺️ Route Summary")
    distance_km = route_summary.get("distance_m", 0) / 1000
    duration_min = route_summary.get("duration_s", 0) / 60
    st.write(f"**Total Distance:** {distance_km:.2f} km")
    st.write(f"**Estimated Duration:** {duration_min:.1f} minutes")
    st.markdown("---")

    # --- STOP DETAILS ---
    st.markdown("### 📍 Stop Details")
    stop_records = []
    for i, stop in enumerate(stops):
        stop_num = "Start Point" if stop["id"].upper() == "START" else f"Stop {i}"
        st.markdown(f"#### 🧭 {stop_num}: {stop.get('id')}")

        if stop.get("address"):
            st.write(f"**Address:** {stop['address']}")
        st.write(f"**Latitude:** {stop['lat']}, **Longitude:** {stop['lon']}")

        if "priority" in stop:
            st.write(f"**Priority:** {stop['priority'].capitalize()}")
        if "package_size" in stop:
            st.write(f"**Package Size:** {stop['package_size'].capitalize()}")

        if i < len(etas):
            try:
                eta_time = datetime.fromisoformat(etas[i])
                eta_str = eta_time.strftime('%Y-%m-%d %H:%M:%S')
                st.write(f"**ETA:** {eta_str}")
            except Exception:
                st.write(f"**ETA:** {etas[i]}")
        else:
            eta_str = "N/A"

        if i > 0 and i - 1 < len(segment_minutes):
            travel_time = segment_minutes[i - 1]
            st.write(f"**Travel Time from Previous Stop:** {travel_time:.1f} minutes")

        st.markdown("---")

        stop_records.append({
            "id": stop.get("id"),
            "address": stop.get("address", ""),
            "lat": stop.get("lat"),
            "lon": stop.get("lon"),
            "priority": stop.get("priority", ""),
            "package_size": stop.get("package_size", ""),
            "eta": eta_str
        })

    # --- TIMELINE OVERVIEW ---
    st.markdown("### 🕒 Timeline Overview")
    for s in stop_records:
        st.text(f"{s['eta']} → {s['id']} ({s.get('address', 'N/A')})")

    st.markdown("---")

    # --- FETCH REALISTIC ROUTE GEOMETRY VIA OSRM ---
    st.markdown("### 🗺️ Route Map")

    coords_str = ";".join([f"{stop['lon']},{stop['lat']}" for stop in stops])
    osrm_url = f"http://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"

    try:
        response = requests.get(osrm_url)
        response.raise_for_status()
        osrm_data = response.json()

        if osrm_data.get("routes"):
            geometry = osrm_data["routes"][0]["geometry"]["coordinates"]
        else:
            geometry = []
            st.warning("⚠️ Could not retrieve route geometry; showing straight lines instead.")
    except Exception as e:
        st.warning(f"⚠️ OSRM request failed ({e}); showing straight lines instead.")
        geometry = []

    # --- PREPARE DATA ---
    df = pd.DataFrame(stop_records)
    midpoint = (df["lat"].mean(), df["lon"].mean())

    # --- DEFINE ICON LAYER ---
    icon_data = {
        "url": "https://cdn-icons-png.flaticon.com/512/684/684908.png",
        "width": 128,
        "height": 128,
        "anchorY": 128,
    }

    df["icon_data"] = [icon_data] * len(df)
    icon_layer = pdk.Layer(
        "IconLayer",
        data=df,
        get_icon="icon_data",
        get_position=["lon", "lat"],
        get_size=3,
        pickable=True,
    )

    # --- DEFINE LINE LAYER ---
    if geometry:
        line_layer = pdk.Layer(
            "PathLayer",
            data=[{"path": geometry}],
            get_color=[0, 128, 255],
            width_scale=5,
            get_width=3,
            opacity=0.8,
        )
    else:
        # fallback: straight lines between stops
        route_lines = [
            {"from": [df.iloc[i]["lon"], df.iloc[i]["lat"]],
             "to": [df.iloc[i + 1]["lon"], df.iloc[i + 1]["lat"]]}
            for i in range(len(df) - 1)
        ]
        line_layer = pdk.Layer(
            "LineLayer",
            data=route_lines,
            get_source_position="from",
            get_target_position="to",
            get_color=[255, 100, 0],
            get_width=4,
        )

    # --- RENDER MAP ---
    view_state = pdk.ViewState(latitude=midpoint[0], longitude=midpoint[1], zoom=10)
    r = pdk.Deck(
        layers=[line_layer, icon_layer],
        initial_view_state=view_state,
        tooltip={
            "text": "Stop: {id}\nETA: {eta}\nPriority: {priority}\nPackage: {package_size}"
        },
    )
    st.pydeck_chart(r)

    st.success("✅ Route plan displayed successfully with real road geometry.")



def display_route_plan_marked_map(route_data: dict):
    """
    Displays a delivery route plan in Streamlit with:
    - Real road geometry (via OSRM)
    - Numbered markers showing stop sequence
    - Color-coded priorities (High=Red, Medium=Orange, Low=Green)
    - Interactive map with tooltips
    """

    if not route_data or "stops" not in route_data:
        st.warning("No valid route data provided.")
        return

    stops = route_data["stops"]
    route_summary = route_data.get("route_summary", {})
    segment_minutes = route_data.get("estimated_segment_minutes", [])
    etas = route_data.get("etas", [])

    # --- HEADER ---
    st.subheader("🚚 Delivery Route Plan")
    st.markdown("---")

    # --- ROUTE SUMMARY ---
    st.markdown("### 🗺️ Route Summary")
    distance_km = route_summary.get("distance_m", 0) / 1000
    duration_min = route_summary.get("duration_s", 0) / 60
    st.write(f"**Total Distance:** {distance_km:.2f} km")
    st.write(f"**Estimated Duration:** {duration_min:.1f} minutes")
    st.markdown("---")

    # --- STOP DETAILS ---
    st.markdown("### 📍 Stop Details")
    stop_records = []
    for i, stop in enumerate(stops):
        stop_num = "Start Point" if stop["id"].upper() == "START" else f"Stop {i}"
        st.markdown(f"#### 🧭 {stop_num}: {stop.get('id')}")

        if stop.get("address"):
            st.write(f"**Address:** {stop['address']}")
        st.write(f"**Latitude:** {stop['lat']}, **Longitude:** {stop['lon']}")

        if "priority" in stop:
            st.write(f"**Priority:** {stop['priority'].capitalize()}")
        if "package_size" in stop:
            st.write(f"**Package Size:** {stop['package_size'].capitalize()}")

        if i < len(etas):
            try:
                eta_time = datetime.fromisoformat(etas[i])
                eta_str = eta_time.strftime('%Y-%m-%d %H:%M:%S')
                st.write(f"**ETA:** {eta_str}")
            except Exception:
                st.write(f"**ETA:** {etas[i]}")
        else:
            eta_str = "N/A"

        if i > 0 and i - 1 < len(segment_minutes):
            travel_time = segment_minutes[i - 1]
            st.write(f"**Travel Time from Previous Stop:** {travel_time:.1f} minutes")

        st.markdown("---")

        stop_records.append({
            "seq": i,
            "id": stop.get("id"),
            "address": stop.get("address", ""),
            "lat": stop.get("lat"),
            "lon": stop.get("lon"),
            "priority": stop.get("priority", "low"),
            "package_size": stop.get("package_size", ""),
            "eta": eta_str
        })

    # --- TIMELINE OVERVIEW ---
    st.markdown("### 🕒 Timeline Overview")
    for s in stop_records:
        st.text(f"{s['eta']} → {s['id']} ({s.get('address', 'N/A')})")

    st.markdown("---")

    # --- FETCH REALISTIC ROUTE GEOMETRY VIA OSRM ---
    st.markdown("### 🗺️ Route Map")

    coords_str = ";".join([f"{stop['lon']},{stop['lat']}" for stop in stops])
    osrm_url = f"http://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"

    try:
        response = requests.get(osrm_url)
        response.raise_for_status()
        osrm_data = response.json()

        if osrm_data.get("routes"):
            geometry = osrm_data["routes"][0]["geometry"]["coordinates"]
        else:
            geometry = []
            st.warning("⚠️ Could not retrieve route geometry; showing straight lines instead.")
    except Exception as e:
        st.warning(f"⚠️ OSRM request failed ({e}); showing straight lines instead.")
        geometry = []

    # --- PREPARE DATA ---
    df = pd.DataFrame(stop_records)
    midpoint = (df["lat"].mean(), df["lon"].mean())

    # --- Assign color based on priority ---
    def get_color(priority):
        if str(priority).lower() == "high":
            return [255, 0, 0]     # Red
        elif str(priority).lower() == "medium":
            return [255, 140, 0]   # Orange
        else:
            return [0, 180, 0]     # Green

    df["color"] = df["priority"].apply(get_color)



    # --- ICONS WITH NUMBERS ---
    df["label"] = df["seq"].apply(lambda x: "S" if x == 0 else str(x))
    text_layer = pdk.Layer(
        "TextLayer",
        data=df,
        get_position=["lon", "lat"],
        get_text="label",
        get_color=[255, 255, 255],
        get_size=18,
        get_alignment_baseline="'bottom'",
    )

    circle_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["lon", "lat"],
        get_fill_color="color",
        get_radius=250,
        pickable=True,
    )

    # --- ROUTE LAYER (Real Geometry) ---
    if geometry:
        line_layer = pdk.Layer(
            "PathLayer",
            data=[{"path": geometry}],
            get_color=[0, 128, 255],
            width_scale=5,
            get_width=4,
            opacity=0.8,
        )
    else:
        route_lines = [
            {"from": [df.iloc[i]["lon"], df.iloc[i]["lat"]],
             "to": [df.iloc[i + 1]["lon"], df.iloc[i + 1]["lat"]]}
            for i in range(len(df) - 1)
        ]
        line_layer = pdk.Layer(
            "LineLayer",
            data=route_lines,
            get_source_position="from",
            get_target_position="to",
            get_color=[0, 0, 255],
            get_width=4,
        )

    # --- FINAL MAP RENDER ---
    view_state = pdk.ViewState(latitude=midpoint[0], longitude=midpoint[1], zoom=10)

    r = pdk.Deck(
        layers=[line_layer, circle_layer, text_layer],
        initial_view_state=view_state,
        map_style=pdk.map_styles.LIGHT,
        tooltip={
            "text": "Stop: {id}\nETA: {eta}\nPriority: {priority}\nPackage: {package_size}"
        },
    )

    st.pydeck_chart(r)
    st.caption("Priorities | High = 🔴 Red | Medium = 🟠 Orange | Low = 🟢 Green")
    st.success("✅ Route plan displayed successfully with numbered and color-coded map markers.")




def display_route_plan_folium(route_data: dict, save_path: str = "route_plan.html"):
    """
    Creates and saves an interactive Folium map visualizing the delivery route.
    
    Args:
        route_data (dict): The route plan JSON (as per the provided structure).
        save_path (str): Path to save the generated HTML map (default: route_plan.html).
        
    Returns:
        folium.Map: The generated map object.
    """

    if not route_data or "stops" not in route_data:
        raise ValueError("Invalid route data. Expected a 'stops' key.")

    stops = route_data["stops"]
    segment_minutes = route_data.get("estimated_segment_minutes", [])
    etas = route_data.get("etas", [])

    # Determine map center
    avg_lat = sum(stop["lat"] for stop in stops) / len(stops)
    avg_lon = sum(stop["lon"] for stop in stops) / len(stops)

    # Create map
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=11, control_scale=True)

    # Priority → Color mapping
    color_map = {"high": "red", "medium": "orange", "low": "green"}

    # Plot stops
    coordinates = []
    for i, stop in enumerate(stops):
        lat, lon = stop["lat"], stop["lon"]
        coordinates.append((lat, lon))

        stop_label = "Start" if stop["id"].upper() == "START" else f"Stop {i}"
        color = color_map.get(stop.get("priority", "low").lower(), "blue")

        # ETA handling
        if i < len(etas):
            try:
                eta_time = datetime.fromisoformat(etas[i])
                eta_str = eta_time.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                eta_str = etas[i]
        else:
            eta_str = "N/A"

        # Travel time
        travel_time = (
            f"{segment_minutes[i-1]:.1f} min" if i > 0 and i - 1 < len(segment_minutes) else "N/A"
        )

        popup_html = f"""
        <b>{stop_label} - {stop['id']}</b><br>
        Address: {stop.get('address', 'N/A')}<br>
        Priority: {stop.get('priority', 'N/A').capitalize()}<br>
        Package Size: {stop.get('package_size', 'N/A').capitalize()}<br>
        ETA: {eta_str}<br>
        Travel Time from Previous: {travel_time}
        """

        # Marker with number
        folium.Marker(
            location=(lat, lon),
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{stop_label}: {stop.get('address', 'N/A')}",
            icon=folium.DivIcon(
                html=f"""
                <div style="
                    background-color:{color};
                    color:white;
                    border-radius:50%;
                    text-align:center;
                    font-weight:bold;
                    width:28px;
                    height:28px;
                    line-height:28px;
                    border:2px solid black;
                ">{'S' if stop['id'].upper() == 'START' else i}</div>
                """
            ),
        ).add_to(m)

    # Draw route line
    folium.PolyLine(
        coordinates,
        color="blue",
        weight=4,
        opacity=0.8,
        tooltip="Delivery Route Path",
    ).add_to(m)

    # Add distance/time summary if available
    route_summary = route_data.get("route_summary", {})
    distance_km = route_summary.get("distance_m", 0) / 1000
    duration_min = route_summary.get("duration_s", 0) / 60

    folium.map.Marker(
        [avg_lat, avg_lon],
        icon = plugins.BeautifyIcon(
            icon="info-sign",
            border_color="gray",
            text_color="black",
            background_color="white",
            number=0
        ),
        popup=folium.Popup(
            f"<b>Total Distance:</b> {distance_km:.2f} km<br>"
            f"<b>Estimated Duration:</b> {duration_min:.1f} minutes",
            max_width=250
        ),
    ).add_to(m)

    # Save map to file
    m.save(save_path)
    print(f"✅ Route map saved to {save_path}")

    return m





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
            icon=folium.Icon(color="blue", icon="home", prefix="fa"),
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


def json_to_table(json_data):
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

