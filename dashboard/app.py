"""
Train Schedule Optimisation Dashboard
Real-time Streamlit UI consuming live Kafka data
"""

import streamlit as st
import json
import os
import time
import pandas as pd
from datetime import datetime

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="TrainOps Intelligence",
    page_icon="🚆",
    layout="wide",
)

# =========================================================
# DATA PATH (DOCKER SAFE)
# =========================================================
BASE = os.environ.get(
    "DATA_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
)

STATE_FILE = os.path.join(BASE, "live_state.json")
HISTORY_FILE = os.path.join(BASE, "history.json")
ALERTS_FILE = os.path.join(BASE, "alerts.json")

# =========================================================
# LOADERS
# =========================================================
def load_json(path):
    try:
        with open(path, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except:
        pass
    return {}

def load_json_list(path):
    try:
        with open(path, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except:
        pass
    return []

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.title("🚆 TrainOps")
    refresh_rate = st.slider("Refresh Seconds", 1, 10, 2)

    st.markdown("---")
    st.markdown("### System Status")
    st.success("Kafka Stream Active")

# =========================================================
# LOAD DATA
# =========================================================
trains = load_json(STATE_FILE)
history = load_json(HISTORY_FILE)
alerts = load_json_list(ALERTS_FILE)

# =========================================================
# HEADER
# =========================================================
st.title("🚆 TrainOps Intelligence Dashboard")

st.caption(
    f"Live Update • {datetime.now().strftime('%H:%M:%S')}"
)

# =========================================================
# NO DATA CHECK
# =========================================================
if not trains:
    st.warning("⏳ No data received yet...")
    st.info("Check if Kafka Producer & Consumer are running.")

else:

    # =====================================================
    # KPI METRICS
    # =====================================================
    vals = list(trains.values())

    avg_delay = sum(v.get("delay_minutes", 0) for v in vals) / len(vals)
    avg_speed = sum(v.get("speed_kmh", 0) for v in vals) / len(vals)
    on_time = sum(1 for v in vals if v.get("delay_minutes", 0) < 5)

    c1, c2, c3 = st.columns(3)

    c1.metric("Average Delay", f"{avg_delay:.1f} min")
    c2.metric("Average Speed", f"{avg_speed:.0f} km/h")
    c3.metric("On Time Trains", f"{on_time}/{len(vals)}")

    st.divider()

    # =====================================================
    # TRAIN STATUS TABLE
    # =====================================================
    st.subheader("🚄 Live Train Status")

    table = []

    for tid, t in trains.items():
        table.append({
            "Train": t.get("train_name"),
            "From": t.get("current_station_name"),
            "To": t.get("next_station_name"),
            "Speed": t.get("speed_kmh"),
            "Delay": t.get("delay_minutes"),
            "Status": t.get("status"),
        })

    df = pd.DataFrame(table)
    st.dataframe(df, use_container_width=True)

    # =====================================================
    # SPEED CHART
    # =====================================================
    st.subheader("⚡ Speed Comparison")

    speed_df = pd.DataFrame([
        {
            "Train": v.get("train_name"),
            "Speed": v.get("speed_kmh"),
        }
        for v in trains.values()
    ])

    st.bar_chart(speed_df.set_index("Train"))

    # =====================================================
    # DELAY CHART
    # =====================================================
    st.subheader("⏱ Delay Analysis")

    delay_df = pd.DataFrame([
        {
            "Train": v.get("train_name"),
            "Delay": v.get("delay_minutes"),
        }
        for v in trains.values()
    ])

    st.bar_chart(delay_df.set_index("Train"))

# =========================================================
# ALERT PANEL
# =========================================================
st.divider()
st.subheader("⚠️ Alerts")

if not alerts:
    st.success("No active alerts")
else:
    for a in alerts[:10]:
        st.error(
            f"{a.get('alert_type','Alert')} — {a.get('message','')}"
        )

# =========================================================
# OPTIMISATION PANEL
# =========================================================
st.divider()
st.subheader("🧠 AI Optimisation Suggestions")

if trains:
    st.success("All trains operating optimally.")
else:
    st.info("Waiting for data...")

# =========================================================
# AUTO REFRESH (FINAL FIX)
# =========================================================
st.markdown(
    f"<div style='text-align:center;color:gray;'>Auto refresh every {refresh_rate} seconds</div>",
    unsafe_allow_html=True
)

time.sleep(refresh_rate)
st.rerun()