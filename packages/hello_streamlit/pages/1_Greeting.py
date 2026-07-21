import streamlit as st

from packages.hello_streamlit.shared import greeting

st.title("👋 Greeting")
st.caption("Imports `greeting` from the shared first-party module.")

name = st.text_input("Your name", value="world")
st.success(greeting(name))
