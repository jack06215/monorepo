import streamlit as st

from shared import APP_NAME

st.set_page_config(page_title=APP_NAME, page_icon="👋", layout="wide")

st.title(f"👋 {APP_NAME} — multi-page demo")
st.write(
    "A multi-page Streamlit app built and launched with Bazel via the "
    "`streamlit_app` macro. Use the sidebar to switch pages."
)
st.info(
    "Pages live in `pages/` and share helpers from `shared.py` — everything "
    "is bundled into the binary's runfiles so `streamlit run` finds it."
)
