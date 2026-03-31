"""
Page 2 – Live Route Map
Shows all 5 trains plotted on a geographic map of India with their routes,
current position interpolated from progress_pct, and station markers.
"""

import streamlit as st
import json
import os
import math
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="TrainOps – Route Map", page_icon="🗺️", layout="wide")

BASE       = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "data"))
STATE_FILE = os.path.join(BASE, "live_state.json")

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&family=Space+Mono&display=swap');
* { font-family: 'Barlow Condensed', sans-serif; }
.stApp { background: #0a0f1e; color: #e0e6f0; }
[data-testid="stSidebar"] { background: #060c1a; }
h1,h2,h3 { color: #c8d8f8; }
</style>
""", unsafe_allow_html=True)

# ── Station coordinates ────────────────────────────────────────────────────────
STATION_COORDS = {
    "NDLS": (28.6419, 77.2194, "New Delhi"),
    "MMCT": (18.9696, 72.8194, "Mumbai Central"),
    "MAS":  (13.0827, 80.2707, "Chennai Central"),
    "HWH":  (22.5839, 88.3424, "Howrah Junction"),
    "SC":   (17.4344, 78.5013, "Secunderabad"),
    "AGC":  (27.1592, 78.0082, "Agra Cantt"),
    "BPL":  (23.2639, 77.4126, "Bhopal Junction"),
    "NGP":  (21.1458, 79.0882, "Nagpur Junction"),
    "PUNE": (18.5279, 73.8742, "Pune Junction"),
    "JP":   (26.9124, 75.7873, "Jaipur Junction"),
    "LKO":  (26.8467, 80.9462, "Lucknow NR"),
    "VSKP": (17.6868, 83.2185, "Visakhapatnam"),
    "SBC":  (12.9762, 77.5993, "Bangalore City"),
    "ALD":  (25.4358, 81.8463, "Prayagraj Jn"),
    "KOTA": (25.1802, 75.8333, "Kota Junction"),
}

TRAIN_ROUTES = {
    "12951": (["NDLS","AGC","KOTA","BPL","MMCT"],         "#E63946"),
    "12301": (["NDLS","ALD","HWH"],                        "#2196F3"),
    "22691": (["NDLS","AGC","BPL","NGP","SC","SBC"],       "#FF9800"),
    "12627": (["NDLS","AGC","BPL","NGP","SC","MAS","SBC"], "#9C27B0"),
    "12839": (["MMCT","PUNE","NGP","SC","VSKP","HWH"],     "#00BCD4"),
}

def interpolate_position(from_code, to_code, progress):
    """Linear interpolation between two station coordinates."""
    if from_code not in STATION_COORDS or to_code not in STATION_COORDS:
        return STATION_COORDS.get(from_code, (20.5, 78.9, ""))[:2]
    lat1, lng1, _ = STATION_COORDS[from_code]
    lat2, lng2, _ = STATION_COORDS[to_code]
    t = progress / 100.0
    return lat1 + (lat2 - lat1) * t, lng1 + (lng2 - lng1) * t

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("## 🗺️ Live Route Map — Indian Railway Network")
col_ts, col_ref = st.columns([3,1])
with col_ts:
    st.markdown(f'<span style="color:#3060a0;font-size:13px;">Updated: {datetime.now().strftime("%H:%M:%S")}</span>',
                unsafe_allow_html=True)
with col_ref:
    refresh = st.checkbox("Auto-refresh (3s)", value=True)

trains = load_state()

# ── Build figure ───────────────────────────────────────────────────────────────
fig = go.Figure()

# 1. Draw route lines for each train
for tid, (route, color) in TRAIN_ROUTES.items():
    lats = [STATION_COORDS[s][0] for s in route if s in STATION_COORDS]
    lngs = [STATION_COORDS[s][1] for s in route if s in STATION_COORDS]
    names = [STATION_COORDS[s][2] for s in route if s in STATION_COORDS]
    fig.add_trace(go.Scattergeo(
        lat=lats, lon=lngs,
        mode="lines",
        line=dict(width=2, color=color),
        opacity=0.35,
        name=f"Route {tid}",
        hoverinfo="skip",
        showlegend=False,
    ))

# 2. Station markers
st_lats  = [v[0] for v in STATION_COORDS.values()]
st_lngs  = [v[1] for v in STATION_COORDS.values()]
st_names = [f"{code} – {v[2]}" for code, v in STATION_COORDS.items()]
st_codes = list(STATION_COORDS.keys())

fig.add_trace(go.Scattergeo(
    lat=st_lats, lon=st_lngs,
    mode="markers+text",
    marker=dict(size=7, color="#1e3058", line=dict(color="#448aff", width=1.5)),
    text=st_codes,
    textposition="top center",
    textfont=dict(size=9, color="#7090c0", family="Space Mono"),
    hovertext=st_names,
    hoverinfo="text",
    name="Stations",
    showlegend=True,
))

# 3. Live train positions
delay_color_map = lambda d: "#00e676" if d < 5 else ("#ff9100" if d < 15 else "#ff1744")

for tid, tdata in trains.items():
    if tid not in TRAIN_ROUTES:
        continue
    prog   = tdata.get("progress_pct", 0)
    from_s = tdata.get("current_station", "NDLS")
    to_s   = tdata.get("next_station", "AGC")
    color  = TRAIN_ROUTES[tid][1]
    delay  = tdata.get("delay_minutes", 0)
    dcolor = delay_color_map(delay)
    lat, lng = interpolate_position(from_s, to_s, prog if not tdata.get("at_station") else 100)

    hover = (
        f"<b>{tdata.get('train_name','')}</b><br>"
        f"Train #{tid}<br>"
        f"Status: {tdata.get('status','')}<br>"
        f"Speed: {tdata.get('speed_kmh',0):.0f} km/h<br>"
        f"Delay: {delay:.1f} min<br>"
        f"Progress: {prog:.1f}%<br>"
        f"Weather: {tdata.get('weather','')}<br>"
        f"Signal: {tdata.get('signal_status','')}"
    )

    # Pulse ring
    fig.add_trace(go.Scattergeo(
        lat=[lat], lon=[lng],
        mode="markers",
        marker=dict(size=22, color=color, opacity=0.15),
        hoverinfo="skip", showlegend=False,
    ))
    # Main dot
    fig.add_trace(go.Scattergeo(
        lat=[lat], lon=[lng],
        mode="markers+text",
        marker=dict(
            size=14, color=color,
            symbol="circle",
            line=dict(color=dcolor, width=2),
        ),
        text=[tid],
        textposition="middle right",
        textfont=dict(size=10, color="#e8f0fe", family="Space Mono"),
        hovertext=[hover],
        hoverinfo="text",
        name=tdata.get("train_name", tid),
        showlegend=True,
    ))

# ── Map layout ─────────────────────────────────────────────────────────────────
fig.update_geos(
    visible=False,
    resolution=50,
    scope="asia",
    center=dict(lat=22, lon=80),
    projection_scale=4.5,
    showland=True,    landcolor="#0d1b2e",
    showocean=True,   oceancolor="#060c1a",
    showlakes=True,   lakecolor="#060c1a",
    showrivers=True,  rivercolor="#0a1525",
    showcountries=True, countrycolor="#1a3060",
    showsubunits=True,  subunitcolor="#1a2a40",
    showcoastlines=True, coastlinecolor="#1a3060",
)
fig.update_layout(
    paper_bgcolor="#0a0f1e",
    plot_bgcolor="#0a0f1e",
    font_color="#c8d8f8",
    height=620,
    margin=dict(l=0, r=0, t=0, b=0),
    legend=dict(
        bgcolor="rgba(13,27,46,0.9)",
        bordercolor="#1a3060",
        borderwidth=1,
        font=dict(size=11, color="#c8d8f8"),
        x=0.01, y=0.99,
    ),
    hoverlabel=dict(
        bgcolor="#0d1b2e",
        bordercolor="#1a3060",
        font=dict(family="Barlow Condensed", size=13, color="#e8f0fe"),
    ),
)

st.plotly_chart(fig, use_container_width=True)

# ── Train position table ────────────────────────────────────────────────────────
if trains:
    st.divider()
    st.markdown("### 📍 Current Positions")
    rows = []
    for tid, t in trains.items():
        rows.append({
            "Train ID":   tid,
            "Name":       t.get("train_name",""),
            "Type":       t.get("train_type",""),
            "From":       t.get("current_station",""),
            "To":         t.get("next_station",""),
            "Progress %": f"{t.get('progress_pct',0):.1f}",
            "Speed km/h": f"{t.get('speed_kmh',0):.1f}",
            "Delay min":  f"{t.get('delay_minutes',0):.1f}",
            "Weather":    t.get("weather",""),
            "Signal":     t.get("signal_status",""),
            "Status":     t.get("status",""),
        })
    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Delay min": st.column_config.NumberColumn(format="%.1f ⏱"),
            "Speed km/h": st.column_config.NumberColumn(format="%.1f 🚄"),
            "Progress %": st.column_config.ProgressColumn(min_value=0, max_value=100),
        }
    )

# Auto-refresh
if refresh:
    import time
    time.sleep(3)
    st.rerun()
