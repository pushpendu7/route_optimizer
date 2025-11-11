import utils.utils as utils
import folium
import bkp.config as config
import pandas as pd
import streamlit as st
from datetime import datetime
from streamlit_folium import st_folium
from models import train_and_save_model
from api_clients import get_static_map_image_url
from agents import ClusteringAgent, PlannerAgent, OptimizerAgent, MonitorAgent, DispatcherAgent, DataGeneratorAgent


# Set Page Config
st.set_page_config(
    page_title = "AI Logistics Route Optimizer",
    page_icon = "🤖",
    layout = "wide",
    initial_sidebar_state = "expanded"
)

st.markdown(
    f"""
<style>
    .st-emotion-cache-10p9htt:before {{
        content: "𖡎 Route Optimizer";
        font-weight: bold;
        font-size: x-large;
    }}
</style>""",
        unsafe_allow_html=True,
    )


# -------------------------
# Helper to load sample data
DATA_DIR = config.DATA_DIR
DELIVERIES_FILE = config.DELIVERIES_FILE
TRAFFIC_FILE = config.TRAFFIC_FILE
WEATHER_FILE = config.WEATHER_FILE

deliveries = config.deliveries
traffic_feed = config.traffic_feed
weather_feed = config.weather_feed
# -------------------------

# Simple authentication / role selection (demo mode)
st.sidebar.title("User Login")
role = st.sidebar.selectbox("Role", ["Dispatch Operator (Admin)", "Delivery Agent"])
# username = st.sidebar.text_input("Username", value = "demo_user")
if st.sidebar.button("Train Travel Time Calculator model"):
    train_and_save_model()
    st.sidebar.success("Trained and saved travel_time_model.pkl")

st.title(":rainbow[AI Agent for Real-time Logistics Route Optimization]", anchor = False)
# st.markdown(
#     """
#     **Features included**
#     - Multi-agent system (Planner, Optimizer, Monitor, Dispatcher)
#     - Real API hooks (OpenWeatherMap, Mapbox, OpenRouteService) — configure API keys via environment variables
#     - Streamlit UI for Admin & Delivery Agent
#     - Route override and manual dispatch
#     - Map visualization
#     """)
# -------------------------

# Shared controls
st.sidebar.header("Dispatcher Controls")
area = st.sidebar.selectbox("Location", options = config.locations.keys())
# depot = st.sidebar.selectbox("Depot", options = config.locations[area]["depots"])
# start_lat = depot[0]
# start_lon = depot[1]
# instantiate agents
clusterer = ClusteringAgent()
planner = PlannerAgent()
optimizer = OptimizerAgent()
monitor = MonitorAgent(traffic_feed = config.load_json(config.TRAFFIC_FILE), weather_feed = config.load_json(config.WEATHER_FILE))
dispatcher = DispatcherAgent()
data_generator = DataGeneratorAgent()

try:

    if role == "Dispatch Operator (Admin)":
        st.header("Operator / Admin Dashboard")

        tab_locations, tab_route = st.tabs(["Locations", "Route Optimization"])

        with tab_locations:

            option_container = st.container(horizontal = True, vertical_alignment = "center")
            locations = config.locations
            option_container.markdown(":grey[Locations:]", width = "content")
            selected_location = option_container.selectbox("Locations", options = locations.keys(), width = 200, label_visibility = "collapsed")
            with option_container.popover("Overlay", width = "content"):
                show_depots = st.checkbox("Depots", value = True)
                show_bounds = st.checkbox("Bounds", value = True)
                show_deliveries = st.checkbox("Deliveries", value = True)
            
            if selected_location:
                # map_center = locations[selected_location]["center"]
                map_bounds = locations[selected_location]["bounds"]
                depots = locations[selected_location]["depots"]

            with option_container.container(horizontal = True, vertical_alignment = "center", border = True):
                st.markdown(":grey[Orders:]", width = "content")
                n_orders = st.number_input("No. of orders", value = 5, min_value = 1, key = "n_orders", max_value = 20, width = 150, icon = "📦", label_visibility = "collapsed")
                st.markdown(":grey[Proximity (km):]", width = "content")
                proximity_km = st.number_input("Proximity (km)", value = 15, min_value = 1, key = "proximity_km", max_value = 100, width = 150, icon = "📍", label_visibility = "collapsed")
                generate_btn = st.button("Generate", help = "Generate orders", on_click = lambda: data_generator.generate_orders(n_orders, selected_location))
                re_cluster_btn = st.button("Re-Cluster", help = "Cluster orders", disabled = not show_deliveries)
            
            map_center = [(map_bounds["min_lat"] + map_bounds["max_lat"]) / 2, (map_bounds["min_lon"] + map_bounds["max_lon"]) / 2]

            map = folium.Map(location = map_center, zoom_start = 11, control_scale = True)

            if show_bounds:
                folium.Rectangle(
                    bounds=[
                        [map_bounds["min_lat"], map_bounds["min_lon"]],
                        [map_bounds["max_lat"], map_bounds["max_lon"]],
                    ],
                    color = "blue",
                    fill = True,
                    fill_opacity = 0.1,
                    tooltip = selected_location
                ).add_to(map)
            
            if show_depots:
                for i, (lat, lon) in enumerate(depots, start = 1):
                    folium.Marker(
                        [lat, lon],
                        tooltip=f"{selected_location}: Depot {i}",
                        icon = folium.Icon(color = "blue", icon = "warehouse", prefix = "fa")
                    ).add_to(map)

            if re_cluster_btn or show_deliveries:

                clusters, deliveries = clusterer.cluster_delivery_points_hdbscan(config.load_json(config.DELIVERIES_FILE), 2, proximity_km)
                
                for order in deliveries:
                    popup_html = f"""
                    <b>Stop ID:</b> {order['id']}<br>
                    <b>Customer Name:</b> {order.get('customer_name', 'N/A')}<br>
                    <b>Address:</b> {order.get('address', 'N/A')}<br>
                    <b>Priority:</b> {order.get('priority', 'N/A').capitalize()}<br>
                    <b>Package Size:</b> {order.get('package_size', 'N/A').capitalize()}<br>
                    <b>Cluster:</b> {order['cluster_id']}<br>
                    """

                    folium.Marker(
                        [order["lat"], order["lon"]],
                        tooltip = f"<b>{order['cluster_id']}:</b> {order.get('address', 'N/A')}",
                        popup = folium.Popup(popup_html, max_width = 300),
                        icon = folium.Icon(color = order["color"], icon = "info-sign"),
                    ).add_to(map)

                depot_assignments = utils.assign_nearest_depot_to_clusters(clusters, depots)
                
            st_folium(map, width = 700, height = 500, use_container_width = True)

            df = pd.DataFrame(config.load_json(config.DELIVERIES_FILE))

            st.subheader(f":blue[Total {len(df)} Deliveries by {len(clusters.items())} Cluster Zone]", anchor = False)

            for cluster_id, cluster_deliveries in clusters.items():
                st.markdown(f"##### 🚚 {cluster_id} :grey[({len(cluster_deliveries)} deliveries)]", width = "content")
                df_cluster = pd.DataFrame(cluster_deliveries)[["id", "customer_name", "address", "priority", "package_size", "fragile"]]
                st.dataframe(df_cluster, hide_index = True, width = "content")

        with tab_route:
            # -------------------------
            # ROLE: Operator (Admin)
            zone_tabs = st.tabs([i.replace("_", " ") for i in list(clusters.keys())])
            if "route_plans" not in st.session_state:
                st.session_state["route_plans"] = set()

            for i, deliveries in enumerate(clusters.items()):
                zone = deliveries[0]
                zone_orders = deliveries[1]
                for dep in depot_assignments:
                    if dep["cluster_id"] == zone:
                        zone_depot_coordinates = [dep["depot_lat"], dep["depot_lon"]]

                with zone_tabs[i]:
                    with st.container(horizontal = True, vertical_alignment = "center"):
                        st.markdown(f"#### :grey[{zone.replace('_', ' ')} Deliveries]", width = "content")
                        with st.popover("Map Overlay"):
                            show_all_depots = st.checkbox("Show All Depots", key = f"show_all_depots_{zone}")
                    
                    start_lat, start_lon = zone_orders[0]["lat"], zone_orders[0]["lon"]
                    zone_map = folium.Map(location = [start_lat, start_lon], zoom_start = 11, control_scale = True)

                    for order in zone_orders:
                        popup_html = f"""
                        <b>Stop ID:</b> {order['id']}<br>
                        <b>Customer Name:</b> {order.get('customer_name', 'N/A')}<br>
                        <b>Address:</b> {order.get('address', 'N/A')}<br>
                        <b>Priority:</b> {order.get('priority', 'N/A').capitalize()}<br>
                        <b>Package Size:</b> {order.get('package_size', 'N/A').capitalize()}<br>
                        """

                        if show_all_depots:
                            for i, (lat, lon) in enumerate(depots, start = 1):
                                folium.Marker(
                                    [lat, lon],
                                    tooltip = f"{selected_location}: Depot {i}",
                                    icon = folium.Icon(color = "blue", icon = "warehouse", prefix = "fa")
                                ).add_to(zone_map)
                        else:
                            folium.Marker(
                                    zone_depot_coordinates,
                                    tooltip = f"{selected_location}: Depot {i}",
                                    icon = folium.Icon(color = "blue", icon = "warehouse", prefix = "fa")
                                ).add_to(zone_map)

                        color_map = {"high": "red", "medium": "orange", "low": "green"}
                        priority = order.get("priority", "low").lower()
                        color = color_map.get(priority, "gray")

                        folium.Marker(
                            [order["lat"], order["lon"]],
                            tooltip = f"{order.get('address', 'N/A')}",
                            popup = folium.Popup(popup_html, max_width = 300),
                            icon = folium.Icon(color = color, icon = "info-sign"),
                        ).add_to(zone_map)

                    with st.container(horizontal = True, vertical_alignment = "top"):
                        with st.container(horizontal_alignment = "center"):
                            st.markdown(":grey[Delivery Locations]", width = "content")
                            st_folium(zone_map, width = 600, height = 400)
                            st.caption(":grey[Priorities:]  High = 🔴 Red | Medium = 🟠 Orange | Low = 🟢 Green", width = "content")
                            
                            operator_instructions = st.text_area(":grey[Operator Instructions]", key = f"operator_instruction_{zone}", value = "Deliver high-priority first; avoid highways if heavy rain.")

                            if st.button("Optimized Route Plan", key = f"create_plan_{zone}"):
                                ordered_ids = planner.prioritize(zone_orders, operator_instructions)
                                # convert to list of delivery dicts in that order
                                id_map = {d["id"]: d for d in zone_orders}
                                ordered_delivery_dicts = [id_map[i] for i in ordered_ids if i in id_map]
                                plan = optimizer.compute_plan((zone_depot_coordinates[0], zone_depot_coordinates[1]), ordered_delivery_dicts)
                                st.session_state[f"current_plan_{zone}"] = plan
                                st.session_state["route_plans"].add(f"current_plan_{zone}")
                                st.toast("Route Plan generated")

                            

                        with st.container(horizontal_alignment = "center"):
                            st.markdown(":grey[Optimized Route]", width = "content")
                            if f"current_plan_{zone}" in st.session_state:
                                zone_route_plan = st.session_state[f"current_plan_{zone}"]

                                stops = zone_route_plan["stops"]
                                segment_minutes = zone_route_plan.get("estimated_segment_minutes", [])
                                etas = zone_route_plan.get("etas", [])
                                route_summary = zone_route_plan.get("route_summary", {})

                                # Calculate map center
                                depot_start_lat, depot_start_lon = stops[0]["lat"], stops[0]["lon"]

                                # List for route polyline
                                route_coords = [(depot_start_lat, depot_start_lon)]

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
                                    marker_label = f"S" if str(stop["id"]).upper() == "START" else f"{i}"

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
                                        tooltip = f"Stop {i}: {stop.get('address', 'N/A')}",
                                        popup = folium.Popup(popup_html, max_width = 300),
                                        icon = folium.Icon(color = color, icon = marker_label, prefix = "fa"),
                                    ).add_to(zone_map)


                                # Add route line connecting all stops
                                folium.PolyLine(
                                    route_coords,
                                    color = "blue",
                                    weight = 4,
                                    opacity = 0.7,
                                    tooltip = "Planned Route Path",
                                ).add_to(zone_map)

                                st_folium(zone_map, width = 600, height = 400)
                                # Add total route summary
                                distance_km = route_summary.get("distance_m", 0) / 1000
                                duration_min = route_summary.get("duration_s", 0) / 60
                                st.markdown(f"**:grey[Total Distance:]** {distance_km:.2f} km  |  **:grey[Estimated Duration:]** {duration_min:.1f} minutes", width = "content")

                            else:
                                st.info("Plan not generated")

                    if f"current_plan_{zone}" in st.session_state:
                        st.subheader("Manual Override", divider = "grey")
                        
                        st.markdown("You can reorder delivery sequence or skip orders", width = "content")
                        
                        with st.container(horizontal = True, vertical_alignment = "center"):
                            with st.container(horizontal = True, vertical_alignment = "center"):
                                st.markdown(":grey[New delivery sequence (by Order ID):]", width = "content")
                                new_order = st.multiselect("New delivery sequence (by Order ID)", placeholder = "Choose order sequence", label_visibility = "collapsed", options = [val["id"] for val in st.session_state[f"current_plan_{zone}"]["stops"] if val["id"] != "START"])
                            with st.container(horizontal = True, vertical_alignment = "center"):
                                st.markdown(":grey[Skip Order (by Order ID):]", width = "content")
                                skip_order = st.multiselect("Skip Order (by Order ID)", placeholder = "Choose order(s) to skip", label_visibility = "collapsed", options = [val["id"] for val in st.session_state[f"current_plan_{zone}"]["stops"] if val["id"] != "START"])
                        # override_str = st.text_input("New order (comma separated)", key = f"override_str_{zone}")
                        
                        if st.button("Apply Override", key = f"override_btn_{zone}"):
                            if f"current_plan_{zone}" not in st.session_state:
                                st.error("No plan in session to override")
                            else:
                                overrides = {"new_order" : new_order, "skip" : skip_order}
                                st.session_state[f"current_plan_{zone}"] = dispatcher.apply_override(st.session_state[f"current_plan_{zone}"], overrides)
                                st.toast("SUCCESS: Override applied", icon = ":material/thumb_up:")
                                st.rerun()

                        st.subheader("Pending Orders", divider = "grey", anchor = False)
                        st.dataframe(pd.DataFrame(zone_orders), hide_index = True)

                        st.subheader("Monitor Conditions & Auto-Reroute", divider = "grey", anchor = False)
                        with st.container(horizontal = True, border = True):
                            with st.container():
                                with st.container(horizontal = True, vertical_alignment = "bottom"):
                                    st.subheader("🚦Live Traffic Feed", divider = "rainbow", anchor = False)
                                    if st.button(":material/refresh:", help = "Refresh traffic data", key = f"traffic_refresh_{zone}"):
                                        ...
                                utils.st.dataframe(utils.get_traffic_data(traffic_feed), width = "content", hide_index = True)
                                
                            with st.container():
                                with st.container(horizontal = True, vertical_alignment = "bottom"):
                                    st.subheader("🌤️ Live Weather Feed", divider = "rainbow", anchor = False)
                                    if st.button(":material/refresh:", help = "Refresh weather data", key = f"weather_refresh_{zone}"):
                                        data_generator.generate_weather_data(config.load_json(config.DELIVERIES_FILE))
                                        st.rerun()
                                utils.st.dataframe(utils.get_weather_data(config.load_json(config.WEATHER_FILE)), width = "content", hide_index = True)
                                

                            events = monitor.evaluate()

                            with st.container(border = True, height = 500):
                                st.markdown(f"#### 🚨 Detected Events ({len(events)})")
                                severity_color = {
                                                    "high": "red",
                                                    "medium": "orange",
                                                    "low": "green"
                                                }
                                
                                for i, e in enumerate(events, 1):
                                    sev = e.get("severity", "unknown").lower()
                                    color = severity_color.get(sev, "gray")

                                    # Base event header

                                    # Event details
                                    if e["type"] == "traffic":
                                        st.markdown(f"**:blue[Event {i}]** - {e['type'].title()}", unsafe_allow_html = True)

                                        st.markdown(
                                            f"""
                                            - **:grey[Segment:]** `{e.get('segment', 'N/A')}`  
                                            - **:grey[Severity:]** :{color}[{sev.capitalize()}]
                                            """,
                                            unsafe_allow_html=True
                                        )
                                    elif e["type"] == "weather":
                                        st.markdown(f"**:blue[Event {i}]** - {e['type'].title()}", unsafe_allow_html = True)
                                        st.markdown(
                                            f"""
                                            - **:grey[Condition:]** {e.get('condition').title()}
                                            - **:grey[Location:]** ({e.get('lat')}, {e.get('lon')})  
                                            - **:grey[Severity:]** :{color}[{sev.capitalize()}]
                                            """,
                                            unsafe_allow_html=True
                                        )


                        if events:
                            if st.button("Auto replan (considering events)", key = f"replan_{zone}"):
                                # simple behavior: bump any deliveries near event latlon or in high severity
                                st.info("Replanning triggered by monitor events")
                                # We just regenerate ordering with operator instructions + appended 'avoid' if needed
                                ordered_ids = planner.prioritize(config.deliveries, operator_instructions + " Consider avoiding high congestion segments if possible.")
                                id_map = {d["id"]: d for d in config.deliveries}
                                ordered_delivery_dicts = [id_map[i["id"]] for i in ordered_ids if i["id"] in id_map]
                                new_plan = optimizer.compute_plan((start_lat, start_lon), ordered_delivery_dicts)
                                st.session_state["current_plan"] = new_plan
                                st.success("Auto replan complete")



###################################################################

                # ordered_ids = planner.prioritize(zone_orders, operator_instructions)
                # st.write(" -> ".join(str(num) for num in ordered_ids))

                # df_zone_orders = pd.DataFrame(zone_orders)[["id", "address", "priority", "package_size"]]
                # st.dataframe(df_zone_orders, hide_index = True, width = "content")


    #     col1, col2 = st.columns([2,1])
    #     with col1:
    #         st.subheader("Pending Deliveries")
    #         df = pd.DataFrame(config.load_json(config.DELIVERIES_FILE))
    #         st.dataframe(df)
            
    #         st.subheader("Plan Generation")
    #         if st.button("Generate optimized plan now"):
    #             ordered_ids = planner.prioritize(config.deliveries, operator_instructions)
    #             # convert to list of delivery dicts in that order
    #             id_map = {d["id"]: d for d in config.deliveries}
    #             ordered_delivery_dicts = [id_map[i] for i in ordered_ids if i in id_map]
    #             plan = optimizer.compute_plan((start_lat, start_lon), ordered_delivery_dicts)
    #             st.session_state["current_plan"] = plan
    #             st.success("Plan generated and saved in session")
    #         if "current_plan" in st.session_state:
    #             st.subheader("Current Plan Summary")
    #             p = st.session_state["current_plan"]
    #             st.markdown("**Route Map**")
    #             utils.display_route_plan_streamlit(p)

    #             # Show map
    #         st.subheader("Manual Override")
    #         st.markdown("You can reorder delivery sequence by entering a comma-separated list of IDs (e.g. D002,D001,D003)")
    #         override_str = st.text_input("New order (comma separated)", key="override_str")
    #         if st.button("Apply Override"):
    #             if "current_plan" not in st.session_state:
    #                 st.error("No plan in session to override")
    #             else:
    #                 new_order = [s.strip() for s in override_str.split(",") if s.strip()]
    #                 override = {"type":"reorder", "new_order": new_order}
    #                 st.session_state["current_plan"] = dispatcher.apply_override(st.session_state["current_plan"], override)
    #                 st.success("Override applied")
    #     with col2:
    #         st.subheader("Live Traffic Feed")
    #         # st.json(traffic_feed)
    #         # utils.display_dict_in_streamlit_nested(traffic_feed)
    #         utils.st.dataframe(utils.json_to_table(traffic_feed))
    #         st.subheader("Live Weather Feed")
    #         # st.json(weather_feed)
    #         # utils.display_dict_in_streamlit_nested(weather_feed)
    #         utils.st.dataframe(utils.json_to_table(weather_feed))

    #     st.markdown("---")
    #     st.subheader("Monitor & Auto-Reroute")
    #     events = monitor.evaluate()
    #     st.write("Detected events:", events)
    #     # display_dict_in_streamlit_nested(events)

    #     if events:
    #         if st.button("Auto replan (considering events)"):
    #             # simple behavior: bump any deliveries near event latlon or in high severity
    #             st.info("Replanning triggered by monitor events")
    #             # We just regenerate ordering with operator instructions + appended 'avoid' if needed
    #             ordered_ids = planner.prioritize(config.deliveries, operator_instructions + " Consider avoiding high congestion segments if possible.")
    #             id_map = {d["id"]: d for d in config.deliveries}
    #             ordered_delivery_dicts = [id_map[i["id"]] for i in ordered_ids if i["id"] in id_map]
    #             new_plan = optimizer.compute_plan((start_lat, start_lon), ordered_delivery_dicts)
    #             st.session_state["current_plan"] = new_plan
    #             st.success("Auto replan complete")

    # -------------------------
# ROLE: Delivery Agent
    else:
        st.header("Delivery Agent Dashboard")
        st.subheader("Assigned Route", anchor = False)
        if len(st.session_state["route_plans"]) == 0:
            st.info("No plan yet — Operator must generate a plan.")

        # if "current_plan" not in st.session_state:
        #     st.info("No plan yet — Operator must generate a plan.")
        else:
            agent_list = []
            for i in range(len(list(st.session_state["route_plans"]))):
                agent_list.append(f"Agent_{i}")

            agent_tabs = st.tabs(agent_list)

            # for i, plan in enumerate(list(st.session_state["route_plans"])):
            for i, agent_route_plan in enumerate(list(st.session_state["route_plans"])):
                with agent_tabs[i]:
                    with st.container(horizontal = True):
                        with st.container(horizontal_alignment = "center"):
                            plan = st.session_state[agent_route_plan]
                            st.markdown(f"#### :grey[Delivery Sequence ({len(plan['stops'])-1} orders)]", width = "content")
                            with st.container(border = True, horizontal_alignment = "center", vertical_alignment = "center"):
                                for idx, stop in enumerate(plan["stops"]):
                                    if stop.get("id") == "START":
                                        st.markdown(f"**:grey[START:] Depot**", width = "content")
                                    else:
                                        st.markdown(":grey[:material/arrow_downward:]", width = "content")
                                        st.markdown(f"**:blue[Stop {idx}:] ID: {stop['id']}** — :grey[Address:] {stop.get('address','')}", width = "content")
                                        # st.markdown(f"**:grey[Stop {idx}:] Order ID: {stop['id']}** — :grey[Address:] {stop.get('address', '')}<br>"
                                        #     f"{'*:grey[ETA: ' + str(plan['etas'][idx-1]) + ']*' if idx-1 < len(plan.get('etas', [])) else ''}",
                                        #     unsafe_allow_html = True, width = "content")
                                        
                                        # Arrival ETA if available
                                        if idx-1 < len(plan.get("etas",[])):
                                            st.caption(f"ETA: {datetime.fromisoformat(plan['etas'][idx-1]).strftime('%B %d, %Y %I:%M:%S %p')}", width = "content")
                        
                        with st.container(horizontal_alignment = "center"):
                            st.markdown("#### :grey[Map View]", width = "content")
                            try:
                                start_lat, start_lon = plan["stops"][0]["lat"], plan["stops"][0]["lon"]
                                agent_map = folium.Map(location = [start_lat, start_lon], zoom_start = 12)
                                
                                folium.Marker(
                                                [start_lat, start_lon], 
                                                tooltip = "Depot", 
                                                icon = folium.Icon(color = "blue", icon = "warehouse", prefix = "fa")
                                            ).add_to(agent_map)
                                
                                for j, stop in enumerate(plan["stops"]):
                                    if stop.get("id") == "START":
                                        continue
                                    folium.Marker(
                                                    [stop["lat"], stop["lon"]], 
                                                    tooltip = f"{stop['address']}",
                                                    icon = folium.Icon(color = "red", icon = f"S" if str(stop["id"]).upper() == "START" else f"{j}", prefix = "fa"),
                                                ).add_to(agent_map)
                                

                                agent_route_coords = [(start_lat, start_lon)]

                                # Add delivery stops
                                for k, stop in enumerate(plan["stops"]):
                                    if stop.get("id") == "START":
                                        continue

                                    lat, lon = stop["lat"], stop["lon"]
                                    agent_route_coords.append((lat, lon))

                                folium.PolyLine(
                                                    agent_route_coords,
                                                    color = "blue",
                                                    weight = 4,
                                                    opacity = 0.7,
                                                    tooltip = "Planned Route Path",
                                                ).add_to(agent_map)


                                st_folium(agent_map, width = 700, height = 500)
                            
                            except Exception as e:
                                st.exception(e)


            # plan = st.session_state["current_plan"]
            
            # st.write("Sequence:")
            # for idx, stop in enumerate(plan["stops"]):
            #     if stop.get("id") == "START":
            #         st.markdown(f"**{idx}. Depot** ({stop['lat']}, {stop['lon']})")
            #     else:
            #         st.markdown(f"**{idx}. {stop['id']}** — {stop.get('address','')}")
            #         # arrival ETA if available
            #         if idx-1 < len(plan.get("etas",[])):
            #             st.caption(f"ETA: {plan['etas'][idx-1]}")
            # st.subheader("Map View")
            # try:
            #     m = folium.Map(location=[start_lat, start_lon], zoom_start=11)
            #     folium.Marker([start_lat, start_lon], tooltip="Depot", icon=folium.Icon(color="green")).add_to(m)
            #     for stop in plan["stops"]:
            #         if stop.get("id") == "START": continue
            #         folium.Marker([stop["lat"], stop["lon"]], tooltip=f"{stop['id']}").add_to(m)
            #     st_folium(m, width=700, height=500)
            # except Exception as e:
            #     st.error("Map rendering requires streamlit-folium or folium installed.")
            # st.subheader("Agent Actions")
            # if st.button("Request Reroute (send reason)"):
            #     st.success("Reroute request submitted to operator (demo)")
            # if st.button("Mark current stop as delivered"):
            #     st.success("Marked as delivered (demo)")


except Exception as e:
    st.exception(e)

finally:
    with st.sidebar:
        with st.expander("Session State"):
            utils.display_dict_in_streamlit_nested(st.session_state)
