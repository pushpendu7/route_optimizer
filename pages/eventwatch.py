import streamlit as st
from utils import utils
from pathlib import Path
from config import config
from agents import DataGeneratorAgent, MonitorAgent

# Set Page Config
st.set_page_config(
    page_title = "EventWatch",
    page_icon = "🚨",
)

with st.container(horizontal = True, vertical_alignment = "bottom"):
    st.image(Path(config.ASSETS_DIR, "eventwatch.png"), width = 50)
    st.header(":blue[EventWatch]", divider = "rainbow", anchor = False)


option_container = st.container(horizontal = True, vertical_alignment = "center")
locations = config.locations
option_container.markdown(":grey[Locations:]", width = "content")
selected_location = option_container.selectbox("Locations", options = locations.keys(), width = 200, label_visibility = "collapsed")


data_generator = DataGeneratorAgent()
monitor = MonitorAgent(traffic_feed = utils.load_json(config.TRAFFIC_FILE), weather_feed = utils.load_json(config.WEATHER_FILE)[selected_location] if selected_location in utils.load_json(config.WEATHER_FILE) else {})

cols = st.columns([0.33, 0.33, 0.33])
tile_height = 500
with cols[0]:
    with st.container(border = True, height = tile_height):
        with st.container(horizontal = True, vertical_alignment = "bottom"):
            st.subheader("🚦Live Traffic Feed", divider = "rainbow", anchor = False)
            if st.button(":material/refresh:", help = "Refresh traffic data"):
                pass
        st.dataframe(utils.get_traffic_data(utils.load_json(config.TRAFFIC_FILE)), width = "content", hide_index = True)

with cols[1]:
    with st.container(border = True, height = tile_height):
        with st.container(horizontal = True, vertical_alignment = "bottom"):
            st.subheader("🌤️ Live Weather Feed", divider = "rainbow", anchor = False)
            if st.button(":material/refresh:", help = "Refresh weather data"):
                data_generator.generate_weather_data(utils.load_json(config.DELIVERIES_FILE)[selected_location] if selected_location in utils.load_json(config.DELIVERIES_FILE) else {}, selected_location)
                st.rerun()
        weather_data = utils.get_weather_data(utils.load_json(config.WEATHER_FILE)[selected_location] if selected_location in utils.load_json(config.WEATHER_FILE) else {})
        if len(weather_data) != 0:
            st.dataframe(utils.get_weather_data(utils.load_json(config.WEATHER_FILE)[selected_location] if selected_location in utils.load_json(config.WEATHER_FILE) else {}), width = "content", hide_index = True)
        else:
            st.markdown("*:grey[(No weather data)]*")
with cols[2]:
    with st.container(border = True, horizontal_alignment = "center", height = tile_height):
        with st.container(horizontal = True, vertical_alignment = "bottom"):
            st.subheader("📰 News Feed", divider = "rainbow", anchor = False)
            if st.button(":material/refresh:", help = "Refresh news data"):
                pass
        st.markdown("*:grey[(No disruptive news)]*")

# custom_css = """
# <style>
# .st-emotion-cache-e4qjpp .e1wguzas4 { /* This class targets a Streamlit container */
#     background-color: rgba(100, 100, 200, 0.3) !important; /* Semi-transparent black */
#     /* Or for fully transparent: background-color: rgba(0, 0, 0, 0) !important; */
# }
# </style>
# """

# st.markdown(custom_css, unsafe_allow_html=True)


events = monitor.evaluate()

with st.container(border = True):
    st.markdown(f"#### 🚨 Detected Events ({len(events)})")
    severity_color = {
                        "high": "red",
                        "medium": "orange",
                        "low": "green"
                    }
    
    with st.container(horizontal = True):
        for i, e in enumerate(events, 1):
            sev = e.get("severity", "unknown").lower()
            color = severity_color.get(sev, "gray")

            # Base event header

            # Event details
            if e["type"] == "traffic":
                with st.container():
                    st.markdown(f"**:blue[Event {i}]** - {e['type'].title()}", width = "content", unsafe_allow_html = True)

                    st.markdown(
                        f"""
                        - **:grey[Segment:]** `{e.get('segment', 'N/A')}`  
                        - **:grey[Severity:]** :{color}[{sev.capitalize()}]
                        """,
                        width = "content", 
                        unsafe_allow_html = True
                    )
            elif e["type"] == "weather":
                with st.container():
                    st.markdown(f"**:blue[Event {i}]** - {e['type'].title()}", width = "content", unsafe_allow_html = True)
                    st.markdown(
                        f"""
                        - **:grey[Condition:]** {e.get('condition').title()}
                        - **:grey[Location:]** ({e.get('lat')}, {e.get('lon')})  
                        - **:grey[Severity:]** :{color}[{sev.capitalize()}]
                        """,
                        width = "content", 
                        unsafe_allow_html=True
                    )