"""
Streamlit Optimisation Page
Shows recommendations from the optimiser module
"""

import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="TrainOps – Optimiser", page_icon="🔧", layout="wide")

BASE    = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
OPT_FILE   = os.path.join(BASE, "optimisations.json")
STATE_FILE = os.path.join(BASE, "live_state.json")
HIST_FILE  = os.path.join(BASE, "history.json")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Barlow+Condensed:wght@400;600;700&display=swap');
* { font-family: 'Barlow Condensed', sans-serif; }
.stApp { background: #0a0f1e; color: #e0e6f0; }
[data-testid="stSidebar"] { background: #060c1a; }
.rec-card {
    background: #0d1b2e; border: 1px solid #1a3060;
    border-left: 4px solid var(--c); border-radius: 6px;
    padding: 12px 16px; margin: 6px 0;
}
.score-pill {
    display: inline-block; padding: 2px 12px; border-radius: 20px;
    background: #1a3060; color: #448aff;
    font-family: 'Space Mono'; font-size: 12px; font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

st.markdown("## 🔧 Schedule Optimisation Engine")
st.markdown("*Live recommendations based on real-time Kafka stream*")
st.divider()

ACTION_COLOR = {
    "REDUCE_HALT":      "#00e676",
    "TRACK_MAINTENANCE": "#ff9100",
    "SIGNAL_PRIORITY":  "#448aff",
    "SPACING":          "#ea80fc",
}
ACTION_ICON = {
    "REDUCE_HALT":      "⏱",
    "TRACK_MAINTENANCE": "🛤",
    "SIGNAL_PRIORITY":  "🚦",
    "SPACING":          "↔️",
}

try:
    with open(OPT_FILE) as f:
        opt = json.load(f)
except Exception:
    st.warning("⏳ Optimiser not yet running. Start the consumer service.")
    st.stop()

# KPIs
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("Trains Monitored", opt.get("total_trains",0))
with c2: st.metric("Avg Delay", f"{opt.get('avg_delay_min',0):.1f} min")
with c3: st.metric("Recommendations", len(opt.get("recommendations",[])))
with c4: st.metric("Est. Time Savings", f"{opt.get('estimated_total_gain_min',0):.1f} min")

st.divider()

recs = opt.get("recommendations", [])
if not recs:
    st.success("✅ No optimisations needed — all trains running smoothly!")
else:
    col_list, col_chart = st.columns([3, 2])
    with col_list:
        st.markdown("### 📋 Recommendations (ranked by impact × priority)")
        for i, r in enumerate(recs, 1):
            c = ACTION_COLOR.get(r["action"], "#448aff")
            icon = ACTION_ICON.get(r["action"], "•")
            st.markdown(f"""
            <div class="rec-card" style="--c:{c}">
              <div style="display:flex;justify-content:space-between;">
                <div>
                  <span style="font-size:11px;background:{c}22;color:{c};
                        padding:1px 8px;border-radius:3px;font-weight:700;letter-spacing:1px;">
                    {icon} {r['action'].replace('_',' ')}
                  </span>
                  &nbsp;<span style="font-size:11px;color:#3060a0;">#{i}</span>
                </div>
                <span class="score-pill">+{r['expected_gain_min']:.1f} min | score {r['score']}</span>
              </div>
              <div style="margin-top:8px;font-size:15px;color:#c8d8f8;">{r['recommendation']}</div>
              <div style="font-size:11px;color:#3060a0;margin-top:4px;">
                {'Train: ' + r['train'] if 'train' in r else ''}
                {'Segment: ' + r['segment'] if 'segment' in r else ''}
              </div>
            </div>""", unsafe_allow_html=True)

    with col_chart:
        st.markdown("### 📊 Impact by Action Type")
        by_action = {}
        for r in recs:
            by_action[r["action"]] = by_action.get(r["action"], 0) + r["expected_gain_min"]
        if by_action:
            fig = go.Figure(go.Bar(
                x=list(by_action.values()),
                y=[a.replace("_"," ") for a in by_action.keys()],
                orientation="h",
                marker_color=[ACTION_COLOR.get(a,"#448aff") for a in by_action.keys()],
                text=[f"+{v:.1f} min" for v in by_action.values()],
                textposition="outside",
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,46,0.8)",
                font_color="#c8d8f8", height=280, margin=dict(l=0,r=60,t=20,b=0),
                xaxis=dict(gridcolor="#1a3060",title="Minutes Saved"),
                yaxis=dict(gridcolor="#1a3060"),
            )
            st.plotly_chart(fig, use_container_width=True)

# Historical delay trend
try:
    with open(HIST_FILE) as f:
        history = json.load(f)
    if history:
        st.divider()
        st.markdown("### 📈 Delay Trend by Train")
        fig2 = go.Figure()
        train_colors = {"12951":"#E63946","12301":"#2196F3","22691":"#FF9800","12627":"#9C27B0","12839":"#00BCD4"}
        for tid, records in history.items():
            df = pd.DataFrame(records[-60:])
            if "delay_min" not in df.columns or df.empty:
                continue
            fig2.add_trace(go.Scatter(
                x=list(range(len(df))), y=df["delay_min"],
                name=tid, mode="lines",
                line=dict(color=train_colors.get(tid,"#448aff"), width=2)
            ))
        fig2.add_hline(y=5,  line_dash="dot", line_color="#ff9100", annotation_text="Minor Delay")
        fig2.add_hline(y=15, line_dash="dot", line_color="#ff1744", annotation_text="Major Delay")
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,46,0.8)",
            font_color="#c8d8f8", height=280, margin=dict(l=0,r=0,t=20,b=0),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            xaxis=dict(gridcolor="#1a3060"), yaxis=dict(gridcolor="#1a3060", title="Delay (min)"),
        )
        st.plotly_chart(fig2, use_container_width=True)
except Exception:
    pass

st.caption(f"Last optimised: {opt.get('generated_at','N/A')}")
