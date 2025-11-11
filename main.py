import streamlit as st
from pathlib import Path
from config import config
from utils import utils

st.markdown(
    f"""
<style>
    .st-emotion-cache-10p9htt:before {{
        content: "𖡎 RouteMind AI";
        font-weight: bold;
        font-size: x-large;
    }}
</style>""",
        unsafe_allow_html=True,
    )

# Set Page Config
st.set_page_config(
    page_title = "RouteMind AI",
    page_icon = "🤖",
    layout = "wide",
    initial_sidebar_state = "expanded"
)

with st.sidebar:
    st.header("Login", anchor = False)
    st.session_state['username'] = st.sidebar.selectbox("Role", config.USERS.keys())
    st.session_state['role'] = config.USERS.get(st.session_state['username'])
    st.markdown(f"""### :grey[*Welcome,*] <br> **{st.session_state['username']}**""", unsafe_allow_html = True)
    st.divider()

main_apps = config.MAIN_APPS
user_main_apps = []


if st.session_state['role'] == "admin":
    user_main_apps = main_apps

else:
    for app1 in main_apps:
        if len(set([st.session_state['role']]).intersection(set(app1["access_privilege_role"]))) > 0:
            user_main_apps.append(app1)

def get_streamlit_pages(apps):
    pages = []
    for app in apps:
        page = st.Page(Path(config.PAGES_DIR, app["page"]), title = app["name"], icon = app["page_icon"])
        pages.append(page)
    return pages

pages = {
    "Home": [
        st.Page(Path(config.PAGES_DIR, "home.py"), title = "Homepage", icon = ":material/home:", default = True),
    ],
    "Apps": get_streamlit_pages(user_main_apps),
    "Help": [
        st.Page(Path(config.PAGES_DIR, "about.py"), title = "About", icon = ":material/info:"),
    ]
}


page = st.navigation(pages, position = "top", expanded = True)
page.run()


with st.sidebar:
    # st.divider()
    with st.expander("Session State"):
        utils.display_dict_in_streamlit_nested(st.session_state)

