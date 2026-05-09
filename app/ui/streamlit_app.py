import json

import requests
import streamlit as st

st.title("Financial Stock Intelligence Agent (MVP)")
watchlist_input = st.text_input("Watchlist (comma-separated)", "AAPL,MSFT,NVDA")

if st.button("Run Analysis"):
    watchlist = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]
    response = requests.post("http://localhost:8000/analyze", json={"watchlist": watchlist}, timeout=60)
    if response.ok:
        st.success("Analysis complete.")
        st.json(response.json())
    else:
        st.error(f"Request failed: {response.status_code}")
        st.code(json.dumps(response.json(), indent=2))
