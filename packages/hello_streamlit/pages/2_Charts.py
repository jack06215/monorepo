import random

import pandas as pd
import streamlit as st

st.title("📈 Charts")
st.caption("Uses pandas — a third-party dep flowing through to the app subprocess.")

random.seed(0)
totals = [0.0, 0.0, 0.0]
rows = []
for _ in range(30):
    totals = [t + random.gauss(0, 1) for t in totals]
    rows.append(list(totals))

df = pd.DataFrame(rows, columns=["a", "b", "c"])
st.line_chart(df)
st.bar_chart(df.tail(10))
