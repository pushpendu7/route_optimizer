import folium
import pandas as pd
import streamlit as st
from utils import utils
from pathlib import Path
from config import config
from datetime import datetime
from streamlit_folium import st_folium
from agents import PlannerAgent, OptimizerAgent, DispatcherAgent

# Set Page Config
st.set_page_config(
    page_title = "RouteBoard",
    page_icon = "🗺️",
)

with st.container(horizontal = True, vertical_alignment = "bottom"):
    st.image(Path(config.ASSETS_DIR, "routeboard.png"), width = 50)
    st.header(":blue[RouteBoard]", divider = "rainbow", anchor = False)

planner = PlannerAgent()
optimizer = OptimizerAgent()
dispatcher = DispatcherAgent()

option_container = st.container(horizontal = True, vertical_alignment = "center")
locations = config.locations
option_container.markdown(":grey[Locations:]", width = "content")
selected_location = option_container.selectbox("Locations", options = locations.keys(), width = 200, label_visibility = "collapsed")
depots = locations[selected_location]["depots"]


if st.session_state['username'] == list(config.USERS.keys())[0]: # --> "Dispatch Operator (Admin)"
    try:
        if selected_location in st.session_state["location"]:
            zone_tabs = st.tabs([i.replace("_", " ") for i in list(st.session_state["location"][selected_location]["clusters"].keys())])

            if "route_plans" not in st.session_state:
                st.session_state["route_plans"] = {}
                st.session_state["route_plans"][selected_location] = set()

            for i, deliveries in enumerate(st.session_state["location"][selected_location]["clusters"].items()):
                zone = deliveries[0]
                zone_orders = deliveries[1]
                
                for dep in st.session_state["location"][selected_location]["depot_assignments"]:
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
                            st_folium(zone_map, width = 600, height = 400, use_container_width = True)
                            st.caption(":grey[Priorities:]  High = 🔴 Red | Medium = 🟠 Orange | Low = 🟢 Green", width = "content")
                            
                            operator_instructions = st.text_area(":grey[Operator Instructions]", key = f"operator_instruction_{zone}", value = "Deliver high-priority first; avoid highways if heavy rain.")

                            if st.button("Optimized Route Plan", key = f"create_plan_{zone}"):
                                ordered_ids = planner.prioritize(zone_orders, operator_instructions)
                                # convert to list of delivery dicts in that order
                                id_map = {d["id"]: d for d in zone_orders}
                                ordered_delivery_dicts = [id_map[i] for i in ordered_ids if i in id_map]
                                plan = optimizer.compute_plan((zone_depot_coordinates[0], zone_depot_coordinates[1]), ordered_delivery_dicts)
                                st.session_state[f"current_plan_{selected_location}_{zone}"] = plan
                                st.session_state["route_plans"][selected_location].add(f"current_plan_{selected_location}_{zone}")
                                st.toast("Route Plan generated")

                            

                        with st.container(horizontal_alignment = "center"):
                            st.markdown(":grey[Optimized Route]", width = "content")
                            if f"current_plan_{selected_location}_{zone}" in st.session_state:
                                zone_route_plan = st.session_state[f"current_plan_{selected_location}_{zone}"]

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

                                st_folium(zone_map, width = 600, height = 400, use_container_width = True)
                                # Add total route summary
                                distance_km = route_summary.get("distance_m", 0) / 1000
                                duration_min = route_summary.get("duration_s", 0) / 60
                                st.markdown(f"**:grey[Total Distance:]** {distance_km:.2f} km  |  **:grey[Estimated Duration:]** {duration_min:.1f} minutes", width = "content")

                            else:
                                st.info("Plan not generated")

                    if f"current_plan_{selected_location}_{zone}" in st.session_state:
                        st.subheader("Manual Override", divider = "grey")
                        
                        st.markdown("You can reorder delivery sequence or skip orders", width = "content")
                        
                        with st.container(horizontal = True, vertical_alignment = "center"):
                            with st.container(horizontal = True, vertical_alignment = "center"):
                                st.markdown(":grey[New delivery sequence (by Order ID):]", width = "content")
                                new_order = st.multiselect("New delivery sequence (by Order ID)", placeholder = "Choose order sequence", label_visibility = "collapsed", options = [val["id"] for val in st.session_state[f"current_plan_{selected_location}_{zone}"]["stops"] if val["id"] != "START"])
                            with st.container(horizontal = True, vertical_alignment = "center"):
                                st.markdown(":grey[Skip Order (by Order ID):]", width = "content")
                                skip_order = st.multiselect("Skip Order (by Order ID)", placeholder = "Choose order(s) to skip", label_visibility = "collapsed", options = [val["id"] for val in st.session_state[f"current_plan_{selected_location}_{zone}"]["stops"] if val["id"] != "START"])
                        # override_str = st.text_input("New order (comma separated)", key = f"override_str_{zone}")
                        
                        if st.button("Apply Override", key = f"override_btn_{zone}"):
                            if f"current_plan_{selected_location}_{zone}" not in st.session_state:
                                st.error("No plan in session to override")
                            else:
                                overrides = {"new_order" : new_order, "skip" : skip_order}
                                st.session_state[f"current_plan_{selected_location}_{zone}"] = dispatcher.apply_override(st.session_state[f"current_plan_{selected_location}_{zone}"], overrides)
                                st.toast("SUCCESS: Override applied", icon = ":material/thumb_up:")
                                st.rerun()

                        st.subheader("Pending Orders", divider = "grey", anchor = False)
                        st.dataframe(pd.DataFrame(zone_orders), hide_index = True)


                        # if events:
                        #     if st.button("Auto replan (considering events)", key = f"replan_{zone}"):
                        #         # simple behavior: bump any deliveries near event latlon or in high severity
                        #         st.info("Replanning triggered by monitor events")
                        #         # We just regenerate ordering with operator instructions + appended 'avoid' if needed
                        #         ordered_ids = planner.prioritize(config.deliveries, operator_instructions + " Consider avoiding high congestion segments if possible.")
                        #         id_map = {d["id"]: d for d in config.deliveries}
                        #         ordered_delivery_dicts = [id_map[i["id"]] for i in ordered_ids if i["id"] in id_map]
                        #         new_plan = optimizer.compute_plan((start_lat, start_lon), ordered_delivery_dicts)
                        #         st.session_state["current_plan"] = new_plan
                        #         st.toast("Auto replan complete")
                        #         st.rerun()
        else:
            st.info(f"Orders not found '{selected_location}' location")
    except KeyError:
        st.info(f"No orders from available from '{selected_location}' location")
    except Exception as e:
        st.exception(e)

else:

    if len(st.session_state["route_plans"]) == 0:
        st.info("No plan yet — Operator must generate a plan.")
    
    else:
        # if len(st.session_state["route_plans"][selected_location]) == 0:
        if selected_location not in st.session_state["route_plans"]:
            st.info(f"No plan generated for {selected_location} location")
        else:
            agent_list = []
            for i in range(len(list(st.session_state["route_plans"][selected_location]))):
                agent_list.append(f"Agent_{i}")

            agent_tabs = st.tabs(agent_list)

            # for i, plan in enumerate(list(st.session_state["route_plans"])):
            for i, agent_route_plan in enumerate(list(st.session_state["route_plans"][selected_location])):
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

                    st.button("Request Reroute", key = f"Request_Reroute_{agent_list[i]}")
                    st.button("Contact Operator", key = f"Contact_Operator_{agent_list[i]}")

    