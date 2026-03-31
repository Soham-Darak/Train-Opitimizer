"""
Page 4 – Analytics
Deep-dive: congestion heatmap, engine health, delay distribution,
passenger load, track utilisation, weather impact analysis.
"""

import streamlit as st
import json
import os
import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="TrainOps – Analytics", page_icon="📊", layout="wide")

BASE       = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "data"))
STATE_FILE = os.path.join(BASE, "live_state.json")
HIST_FILE  = os.path.join(BASE, "history.json")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&family=Space+Mono&display=swap');
* { font-family: 'Barlow Condensed', sans-serif; }
.stApp { background: #0a0f1e; color: #e0e6f0; }
[data-testid="stSidebar"] { background: #060c1a; }
h1,h2,h3 { color: #c8d8f8; }
.chart-card { background:#0d1b2e;border:1px solid #1a3060;border-radius:8px;padding:16px;margin:8px 0; }
.section-header { font-size:11px;font-weight:700;letter-spacing:3px;text-transform:uppercase;
    color:#3060a0;border-bottom:1px solid #1a3060;padding-bottom:6px;margin:16px 0 12px 0; }
</style>
""", unsafe_allow_html=True)

CHART_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(13,27,46,0.8)",
    font_color="#c8d8f8",
    margin=dict(l=10, r=10, t=30, b=10),
)
GRID = dict(gridcolor="#1a3060")

TRAIN_COLORS = {
    "12951":"#E63946","12301":"#2196F3",
    "22691":"#FF9800","12627":"#9C27B0","12839":"#00BCD4",
}
TRAIN_NAMES = {
    "12951":"Mumbai Rajdhani","12301":"Howrah Rajdhani",
    "22691":"SBC Rajdhani",  "12627":"Karnataka Exp", "12839":"Howrah Mail",
}

def load_json(path, default):
    try:
        with open(path) as f: return json.load(f)
    except: return default

trains  = load_json(STATE_FILE, {})
history = load_json(HIST_FILE, {})

st.markdown("## 📊 Analytics — Deep Dive")
st.markdown(f'<span style="color:#3060a0;font-size:13px;">Live snapshot · {datetime.now().strftime("%H:%M:%S")}</span>',
            unsafe_allow_html=True)
st.divider()

if not trains:
    st.warning("⏳ Waiting for data from Kafka stream...")
    st.stop()

# ── Row 1: Speed gauge + Delay distribution + Passenger load ──────────────────
st.markdown('<div class="section-header">Train Health Overview</div>', unsafe_allow_html=True)
r1c1, r1c2, r1c3 = st.columns(3)

with r1c1:
    # Gauge: average speed vs max allowed
    avg_speed = sum(t["speed_kmh"] for t in trains.values()) / len(trains)
    max_speed = max(t["speed_kmh"] for t in trains.values())
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=avg_speed,
        delta={"reference": 100, "valueformat":".1f"},
        title={"text":"Avg Network Speed (km/h)", "font":{"color":"#7090c0","size":13}},
        number={"suffix":" km/h", "font":{"color":"#e8f0fe","size":28,"family":"Space Mono"}},
        gauge={
            "axis":{"range":[0,140],"tickcolor":"#3060a0","tickwidth":1},
            "bar":{"color":"#448aff","thickness":0.3},
            "bgcolor":"#0d1b2e",
            "bordercolor":"#1a3060",
            "steps":[
                {"range":[0,60],  "color":"#0d1b2e"},
                {"range":[60,100],"color":"#0a2030"},
                {"range":[100,140],"color":"#0a1525"},
            ],
            "threshold":{"line":{"color":"#ff1744","width":3},"thickness":0.75,"value":max_speed},
        }
    ))
    fig_gauge.update_layout(**CHART_THEME, height=240)
    st.plotly_chart(fig_gauge, use_container_width=True)

with r1c2:
    # Delay distribution histogram from history
    all_delays = []
    for tid, records in history.items():
        for r in list(records)[-60:]:
            all_delays.append(r.get("delay_min", 0))

    if all_delays:
        fig_hist = go.Figure(go.Histogram(
            x=all_delays,
            nbinsx=20,
            marker_color="#448aff",
            marker_line=dict(color="#0a1525", width=1),
            opacity=0.85,
        ))
        fig_hist.add_vline(x=5, line_dash="dot", line_color="#ff9100",
                           annotation_text="Minor", annotation_font_color="#ff9100")
        fig_hist.add_vline(x=15, line_dash="dot", line_color="#ff1744",
                           annotation_text="Major", annotation_font_color="#ff1744")
        fig_hist.update_layout(
            **CHART_THEME, height=240,
            title="Delay Distribution (last 60 ticks)",
            xaxis=dict(title="Delay (min)", **GRID),
            yaxis=dict(title="Count", **GRID),
        )
        st.plotly_chart(fig_hist, use_container_width=True)

with r1c3:
    # Passenger load bar
    pax_data = pd.DataFrame([
        {"Train": TRAIN_NAMES.get(tid, tid),
         "Passengers": t.get("passengers", 0),
         "Color": TRAIN_COLORS.get(tid,"#448aff")}
        for tid, t in trains.items()
    ])
    fig_pax = go.Figure(go.Bar(
        x=pax_data["Passengers"], y=pax_data["Train"],
        orientation="h",
        marker_color=pax_data["Color"].tolist(),
        text=pax_data["Passengers"].apply(lambda x: f"{x:,}"),
        textposition="outside",
    ))
    fig_pax.add_vline(x=1000, line_dash="dot", line_color="#448aff",
                      annotation_text="Full capacity", annotation_font_color="#448aff")
    fig_pax.update_layout(
        **CHART_THEME, height=240,
        title="Passenger Load",
        xaxis=dict(title="Passengers", **GRID),
        yaxis=dict(**GRID),
    )
    st.plotly_chart(fig_pax, use_container_width=True)

# ── Row 2: Engine health + Congestion over time ────────────────────────────────
st.markdown('<div class="section-header">System Health & Congestion</div>', unsafe_allow_html=True)
r2c1, r2c2 = st.columns([1, 2])

with r2c1:
    # Engine health radial / bar
    eng_data = pd.DataFrame([
        {"Train": TRAIN_NAMES.get(tid, tid)[:16],
         "Health": t.get("engine_health_pct", 100),
         "Color": TRAIN_COLORS.get(tid,"#448aff")}
        for tid, t in trains.items()
    ])
    color_list = [
        "#00e676" if h > 95 else "#ff9100" if h > 90 else "#ff1744"
        for h in eng_data["Health"]
    ]
    fig_eng = go.Figure(go.Bar(
        x=eng_data["Health"], y=eng_data["Train"],
        orientation="h",
        marker_color=color_list,
        text=eng_data["Health"].apply(lambda x: f"{x:.1f}%"),
        textposition="outside",
    ))
    fig_eng.add_vline(x=90, line_dash="dot", line_color="#ff9100",
                      annotation_text="Service threshold")
    fig_eng.update_layout(
        **CHART_THEME, height=280,
        title="Engine Health (%)",
        xaxis=dict(range=[80,102], **GRID),
        yaxis=dict(**GRID),
    )
    st.plotly_chart(fig_eng, use_container_width=True)

with r2c2:
    # Congestion time series from history
    fig_cong = go.Figure()
    for tid, records in history.items():
        df = pd.DataFrame(list(records)[-80:])
        if "congestion" not in df.columns or df.empty:
            continue
        fig_cong.add_trace(go.Scatter(
            x=list(range(len(df))), y=df["congestion"],
            name=TRAIN_NAMES.get(tid, tid),
            mode="lines",
            line=dict(color=TRAIN_COLORS.get(tid,"#448aff"), width=1.5),
            fill="tozeroy",
            fillcolor=TRAIN_COLORS.get(tid,"#448aff") + "18",
        ))
    fig_cong.add_hline(y=60, line_dash="dot", line_color="#ff1744",
                       annotation_text="High Congestion", annotation_font_color="#ff1744")
    fig_cong.update_layout(
        **CHART_THEME, height=280,
        title="Track Congestion % (Rolling)",
        xaxis=dict(title="Ticks", **GRID),
        yaxis=dict(title="Congestion %", range=[0, 100], **GRID),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_cong, use_container_width=True)

# ── Row 3: Weather impact matrix + Track segment utilisation ───────────────────
st.markdown('<div class="section-header">Weather Impact & Track Utilisation</div>', unsafe_allow_html=True)
r3c1, r3c2 = st.columns(2)

with r3c1:
    # Weather vs avg delay heatmap (simulated from current data + weather_delay config)
    WEATHER_DELAY_MAP = {
        "Clear":0,"Cloudy":0,"Fog":5,"Light Rain":2,
        "Heavy Rain":8,"Storm":15,"Heatwave":3
    }
    train_types = ["Rajdhani","Superfast","Mail/Express"]
    weathers    = list(WEATHER_DELAY_MAP.keys())
    z_matrix = []
    for wtype in weathers:
        row = []
        for ttype in train_types:
            base = WEATHER_DELAY_MAP[wtype]
            mult = {"Rajdhani":0.8,"Superfast":1.0,"Mail/Express":1.2}.get(ttype, 1.0)
            row.append(round(base * mult + np.random.uniform(0, 1), 1))
        z_matrix.append(row)

    fig_heat = go.Figure(go.Heatmap(
        z=z_matrix,
        x=train_types,
        y=weathers,
        colorscale=[[0,"#0d1b2e"],[0.3,"#1a4070"],[0.6,"#ff9100"],[1.0,"#ff1744"]],
        text=[[f"{v:.1f}m" for v in row] for row in z_matrix],
        texttemplate="%{text}",
        showscale=True,
        colorbar=dict(title="Avg Delay (min)", tickfont=dict(color="#7090c0")),
    ))
    fig_heat.update_layout(
        **CHART_THEME, height=300,
        title="Weather × Train Type → Expected Delay (min)",
        xaxis=dict(title="Train Type"),
        yaxis=dict(title="Weather"),
    )
    st.plotly_chart(fig_heat, use_container_width=True)

with r3c2:
    # Track segment utilisation
    segments = [
        "NDLS-AGC","AGC-KOTA","KOTA-BPL","BPL-MMCT",
        "NDLS-ALD","ALD-HWH","AGC-BPL","BPL-NGP",
        "NGP-SC","SC-SBC","SC-MAS","MMCT-PUNE","SC-VSKP",
    ]
    # Count how many trains are on each segment right now
    seg_load = {s: 0 for s in segments}
    for t in trains.values():
        seg_key = f"{t.get('current_station','')}-{t.get('next_station','')}"
        rev_key = f"{t.get('next_station','')}-{t.get('current_station','')}"
        if seg_key in seg_load:
            seg_load[seg_key] += 1
        elif rev_key in seg_load:
            seg_load[rev_key] += 1

    seg_df = pd.DataFrame([
        {"Segment": k, "Trains": v,
         "Color": "#ff1744" if v >= 2 else "#ff9100" if v == 1 else "#1a3060"}
        for k, v in seg_load.items()
    ]).sort_values("Trains", ascending=True)

    fig_seg = go.Figure(go.Bar(
        x=seg_df["Trains"], y=seg_df["Segment"],
        orientation="h",
        marker_color=seg_df["Color"].tolist(),
        text=seg_df["Trains"].apply(lambda x: f"{x} train{'s' if x!=1 else ''}"),
        textposition="outside",
    ))
    fig_seg.update_layout(
        **CHART_THEME, height=300,
        title="Live Track Segment Utilisation",
        xaxis=dict(title="Trains on Segment", range=[0,3.5], **GRID),
        yaxis=dict(**GRID),
    )
    st.plotly_chart(fig_seg, use_container_width=True)

# ── Row 4: Speed vs delay scatter + delay recovery trend ──────────────────────
st.markdown('<div class="section-header">Performance Correlation</div>', unsafe_allow_html=True)
r4c1, r4c2 = st.columns(2)

with r4c1:
    scatter_data = pd.DataFrame([
        {
            "Train": TRAIN_NAMES.get(tid, tid),
            "Speed km/h": t["speed_kmh"],
            "Delay min": t["delay_minutes"],
            "Passengers": t.get("passengers", 800),
            "Priority": f"P{t.get('priority',3)}",
            "Color": TRAIN_COLORS.get(tid,"#448aff"),
        }
        for tid, t in trains.items()
    ])
    if not scatter_data.empty:
        fig_sc = go.Figure()
        for _, row in scatter_data.iterrows():
            fig_sc.add_trace(go.Scatter(
                x=[row["Speed km/h"]], y=[row["Delay min"]],
                mode="markers+text",
                marker=dict(size=row["Passengers"]/60, color=row["Color"],
                            line=dict(color="#ffffff", width=1)),
                text=[row["Train"][:12]],
                textposition="top center",
                textfont=dict(size=10, color="#c8d8f8"),
                name=row["Train"],
                showlegend=True,
            ))
        fig_sc.update_layout(
            **CHART_THEME, height=300,
            title="Speed vs Delay (bubble = passenger load)",
            xaxis=dict(title="Speed (km/h)", **GRID),
            yaxis=dict(title="Delay (min)", **GRID),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_sc, use_container_width=True)

with r4c2:
    # Delay rolling average per train
    fig_delay = go.Figure()
    for tid, records in history.items():
        df = pd.DataFrame(list(records)[-80:])
        if "delay_min" not in df.columns or df.empty:
            continue
        # Rolling average
        df["rolling"] = df["delay_min"].rolling(5, min_periods=1).mean()
        fig_delay.add_trace(go.Scatter(
            x=list(range(len(df))), y=df["rolling"],
            name=TRAIN_NAMES.get(tid, tid),
            mode="lines",
            line=dict(color=TRAIN_COLORS.get(tid,"#448aff"), width=2),
        ))
        fig_delay.add_trace(go.Scatter(
            x=list(range(len(df))), y=df["delay_min"],
            mode="lines",
            line=dict(color=TRAIN_COLORS.get(tid,"#448aff"), width=0.5, dash="dot"),
            opacity=0.3, showlegend=False,
        ))
    fig_delay.update_layout(
        **CHART_THEME, height=300,
        title="Delay Trend — Rolling Avg (solid) vs Raw (dotted)",
        xaxis=dict(title="Ticks", **GRID),
        yaxis=dict(title="Delay (min)", **GRID),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_delay, use_container_width=True)

# ── Summary table ──────────────────────────────────────────────────────────────
st.divider()
st.markdown('<div class="section-header">Full Train Data Snapshot</div>', unsafe_allow_html=True)
if trains:
    snap_df = pd.DataFrame([
        {
            "ID": tid,
            "Train": TRAIN_NAMES.get(tid,tid),
            "Type": t["train_type"],
            "Priority": f"P{t['priority']}",
            "Status": t["status"],
            "From": t["current_station"],
            "To": t["next_station"],
            "Speed km/h": round(t["speed_kmh"],1),
            "Delay min": round(t["delay_minutes"],1),
            "Congestion %": t["congestion_pct"],
            "Engine %": round(t["engine_health_pct"],1),
            "Weather": t["weather"],
            "Signal": t["signal_status"],
            "Track": t["track_condition"],
            "Passengers": t["passengers"],
        }
        for tid, t in trains.items()
    ])
    st.dataframe(snap_df, use_container_width=True, hide_index=True)

time.sleep(5)
st.rerun()
