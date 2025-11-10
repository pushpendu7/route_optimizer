import streamlit as st
import pandas as pd
from datetime import datetime
from api_clients import get_static_map_image_url
from agents import ClusteringAgent, PlannerAgent, OptimizerAgent, MonitorAgent, DispatcherAgent, DataGeneratorAgent
from models import train_and_save_model
import utils
import folium
from streamlit_folium import st_folium  # optional; but will use folium embed fallback
import config
st.set_page_config(layout="wide", page_title="AI Logistics Route Optimizer")

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

st.title("AI Agent for Real-time Logistics Route Optimization")
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
operator_instructions = st.sidebar.text_area("Operator Instructions", value = "Deliver high-priority first; avoid highways if heavy rain.")
# instantiate agents
clusterer = ClusteringAgent()
planner = PlannerAgent()
optimizer = OptimizerAgent()
monitor = MonitorAgent(traffic_feed = traffic_feed, weather_feed = weather_feed)
dispatcher = DispatcherAgent()
data_generator = DataGeneratorAgent()


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
        st.markdown(":grey[Orders:]")
        n_orders = st.number_input("No. of orders", value = 5, min_value = 1, key = "n_orders", max_value = 20, width = 150, icon = "📦", label_visibility = "collapsed")
        st.markdown(":grey[Proximity (km):]")
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
        
    st_folium(map, width = 700, height = 400, use_container_width = True)

    df = pd.DataFrame(config.load_json(config.DELIVERIES_FILE))

    st.subheader(f":blue[Total {len(df)} Deliveries by {len(clusters.items())} Cluster Zone]")

    for cluster_id, cluster_deliveries in clusters.items():
        st.markdown(f"##### 🚚 {cluster_id} :grey[({len(cluster_deliveries)} deliveries)]")
        df_cluster = pd.DataFrame(cluster_deliveries)[["id", "customer_name", "address", "priority", "package_size", "fragile"]]
        st.dataframe(df_cluster, hide_index = True, width = "content")

with tab_route:
    # -------------------------
    # ROLE: Operator (Admin)
    if role == "Dispatch Operator (Admin)":
        st.header("Operator / Admin Dashboard")

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

                st_folium(zone_map, width = 700, height = 500)
                st.caption(":grey[Priorities:]  High = 🔴 Red | Medium = 🟠 Orange | Low = 🟢 Green")
                
                if st.button("Optimized Route Plan", key = f"create_plan_{zone}"):
                    ordered_ids = planner.prioritize(zone_orders, operator_instructions)
                    # convert to list of delivery dicts in that order
                    id_map = {d["id"]: d for d in zone_orders}
                    ordered_delivery_dicts = [id_map[i] for i in ordered_ids if i in id_map]
                    plan = optimizer.compute_plan((zone_depot_coordinates[0], zone_depot_coordinates[1]), ordered_delivery_dicts)
                    st.session_state[f"current_plan_{zone}"] = plan
                    st.session_state["route_plans"].add(f"current_plan_{zone}")
                    st.success("Route Plan generated")

                if f"current_plan_{zone}" in st.session_state:
                    st.subheader("Current Plan Summary")
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

                    st_folium(zone_map, width = 700, height = 500)

                        # Add total route summary
                    distance_km = route_summary.get("distance_m", 0) / 1000
                    duration_min = route_summary.get("duration_s", 0) / 60
                    st.markdown(f"**Total Distance:** {distance_km:.2f} km  |  **Estimated Duration:** {duration_min:.1f} minutes")

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
        st.subheader("Assigned Route")
        if len(st.session_state["route_plans"]) == 0:
            st.info("No plan yet — Operator must generate a plan.")

        # if "current_plan" not in st.session_state:
        #     st.info("No plan yet — Operator must generate a plan.")
        else:
            agent_list = []
            for i, agent_route in enumerate(list(st.session_state["route_plans"])):
                agent_list.append(f"Agent_{i}")

            agent_tabs = st.tabs(agent_list)

            # for i, plan in enumerate(list(st.session_state["route_plans"])):
            for i in range(len(list(st.session_state["route_plans"]))):
                with agent_tabs[i]:
                    st.write("Sequence:")
                    plan = st.session_state[list(st.session_state["route_plans"])[i]]
                    for idx, stop in enumerate(plan["stops"]):
                        if stop.get("id") == "START":
                            st.markdown(f"**{idx}. Depot** ({stop['lat']}, {stop['lon']})")
                        else:
                            st.markdown(f"**{idx}. {stop['id']}** — {stop.get('address','')}")
                            # arrival ETA if available
                            if idx-1 < len(plan.get("etas",[])):
                                st.caption(f"ETA: {plan['etas'][idx-1]}")

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


with st.sidebar:
    utils.display_dict_in_streamlit_nested(st.session_state)
