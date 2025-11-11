import folium
import pandas as pd
import streamlit as st
from utils import utils
from pathlib import Path
from config import config
from streamlit_folium import st_folium
from agents import ClusteringAgent, DataGeneratorAgent

# Set Page Config
st.set_page_config(
    page_title = "OrderMap",
    page_icon = "📦",
)

with st.container(horizontal = True, vertical_alignment = "bottom"):
    st.image(Path(config.ASSETS_DIR, "ordermap.png"), width = 50)
    st.header(":blue[OrderMap]", divider = "rainbow", anchor = False)



option_container = st.container(horizontal = True, vertical_alignment = "center")
locations = config.locations
option_container.markdown(":grey[Locations:]", width = "content")
selected_location = option_container.selectbox("Locations", options = locations.keys(), width = 200, label_visibility = "collapsed")
with option_container.popover("Overlay", width = "content"):
    show_depots = st.checkbox("Depots", value = True)
    show_bounds = st.checkbox("Bounds", value = True)
    show_deliveries = st.checkbox("Deliveries", value = True)

if selected_location:
    map_bounds = locations[selected_location]["bounds"]
    depots = locations[selected_location]["depots"]

    st.session_state["location"] = {selected_location: {}}
    st.session_state["depots"] = depots

data_generator = DataGeneratorAgent()
clusterer = ClusteringAgent(selected_location)



cols = st.columns([0.3, 0.7])

with cols[0]:
    with st.container(border = True, horizontal_alignment = "center", vertical_alignment = "center", height = 500):
        st.subheader(":grey[Generate Orders]", divider = "grey")
        st.caption("""Orders are dynamically and synthetically generated using a LLM, which creates realistic delivery data—such as customer details, addresses, coordinates, priorities, and package attributes—based on city-specific parameters and contextual patterns.
                   Clustering is also done to identify delivery zones and the nearest depot from the zone.""")
        st.markdown("")
        with st.container(horizontal = True, horizontal_alignment = "center", vertical_alignment = "center"):
            st.markdown(":grey[No. of Orders:]", width = "content")
            n_orders = st.number_input("No. of orders", value = 5, min_value = 1, key = "n_orders", max_value = 20, width = 150, icon = "📦", label_visibility = "collapsed")
        with st.container(horizontal = True, horizontal_alignment = "center", vertical_alignment = "center"):
            st.markdown(":grey[Proximity (km):]", width = "content")
            proximity_km = st.number_input("Proximity (km)", value = 15, min_value = 1, key = "proximity_km", max_value = 100, width = 150, icon = "📍", label_visibility = "collapsed")
        
        st.markdown("")

        with st.container(horizontal = True, horizontal_alignment = "center"):
            generate_btn = st.button("Generate", help = "Generate orders", type = "primary", on_click = lambda: data_generator.generate_orders(n_orders, selected_location))
            re_cluster_btn = st.button("Re-Cluster", help = "Cluster orders", disabled = not show_deliveries)

with cols[1]:
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
        try:
            clusters, deliveries = clusterer.cluster_delivery_points_hdbscan(utils.load_json(config.DELIVERIES_FILE)[selected_location], 2, proximity_km)
            st.session_state["location"][selected_location]["clusters"] = clusters
            st.session_state["location"][selected_location]["deliveries"] = deliveries

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
            st.session_state["location"][selected_location]["depot_assignments"] = depot_assignments
        except KeyError:
            st.info(f"No orders from available from '{selected_location}' location")
        except Exception as e:
            st.exception(e)
    
    st_folium(map, width = 700, height = 500, use_container_width = True)

if selected_location in utils.load_json(config.DELIVERIES_FILE).keys():
    df = pd.DataFrame(utils.load_json(config.DELIVERIES_FILE)[selected_location])

    st.subheader(f":blue[Total {len(df)} Deliveries in {len(clusters.items())} Cluster Zone]", anchor = False)

    for cluster_id, cluster_deliveries in clusters.items():
        st.markdown(f"##### 🚚 {cluster_id} :grey[({len(cluster_deliveries)} deliveries)]", width = "content")
        df_cluster = pd.DataFrame(cluster_deliveries)[["id", "customer_name", "address", "priority", "package_size", "fragile"]]
        st.dataframe(df_cluster, hide_index = True, width = "stretch")