"""
Page 3 – Schedule Board
Departure-board style view: for each station, show which trains are
scheduled vs actually arriving, their delays, platform, and status.
Mimics the real Indian Railways NTES (National Train Enquiry System).
"""

import streamlit as st
import json
import os
import time
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="TrainOps – Schedule Board", page_icon="📋", layout="wide")

BASE       = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "data"))
STATE_FILE = os.path.join(BASE, "live_state.json")
ALERTS_FILE = os.path.join(BASE, "alerts.json")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow+Condensed:wght@400;600;700&display=swap');
* { font-family: 'Barlow Condensed', sans-serif; }
.stApp { background: #050a14; color: #e0e6f0; }
[data-testid="stSidebar"] { background: #03070f; }

/* Departure board effect */
.board-header {
    background: #020609;
    border: 1px solid #0a2040;
    border-radius: 4px;
    padding: 8px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2px;
}
.board-row {
    background: #050d1a;
    border: 1px solid #0a1e38;
    border-radius: 3px;
    padding: 10px 16px;
    margin: 2px 0;
    display: grid;
    grid-template-columns: 90px 200px 100px 90px 90px 90px 90px 1fr;
    align-items: center;
    transition: background 0.2s;
    font-family: 'Share Tech Mono', monospace;
    font-size: 14px;
}
.board-row:hover { background: #0a1830; }
.on-time  { color: #00e676; }
.delayed  { color: #ff6d00; }
.late     { color: #ff1744; }
.arrived  { color: #448aff; }
.col-head { color: #1a4070; font-size: 11px; letter-spacing: 2px; text-transform: uppercase; }
.blink { animation: blink 1s step-end infinite; }
@keyframes blink { 50% { opacity: 0; } }
.station-tab {
    background: #030810;
    border: 1px solid #0a2040;
    border-radius: 6px 6px 0 0;
    padding: 8px 20px;
    display: inline-block;
    font-size: 13px;
    font-weight: 700;
    color: #3060a0;
    cursor: pointer;
    margin-right: 2px;
}
.station-tab.active { background: #050d1a; color: #c8d8f8; border-bottom: 2px solid #448aff; }
.train-pill {
    display: inline-block; padding: 1px 8px; border-radius: 3px;
    font-size: 11px; font-weight: 700; margin-right: 4px;
}
</style>
""", unsafe_allow_html=True)

# ── Config ─────────────────────────────────────────────────────────────────────
TRAIN_COLORS = {
    "12951": "#E63946", "12301": "#2196F3",
    "22691": "#FF9800", "12627": "#9C27B0", "12839": "#00BCD4",
}
TRAIN_NAMES = {
    "12951": "Mumbai Rajdhani", "12301": "Howrah Rajdhani",
    "22691": "SBC Rajdhani",   "12627": "Karnataka Exp",  "12839": "Howrah Mail",
}

# Full schedule matrix: train_id → station → {arr, dep, halt, platform}
FULL_SCHEDULE = {
    "12951": {
        "NDLS": {"dep":"17:00", "platform":1},
        "AGC":  {"arr":"18:45","dep":"18:47","halt":2, "platform":3},
        "KOTA": {"arr":"21:10","dep":"21:15","halt":5, "platform":1},
        "BPL":  {"arr":"23:50","dep":"00:00","halt":10,"platform":2},
        "MMCT": {"arr":"07:55","platform":5},
    },
    "12301": {
        "NDLS": {"dep":"16:55","platform":4},
        "ALD":  {"arr":"22:20","dep":"22:25","halt":5, "platform":4},
        "HWH":  {"arr":"10:00","platform":8},
    },
    "22691": {
        "NDLS": {"dep":"20:00","platform":2},
        "AGC":  {"arr":"21:50","dep":"21:52","halt":2, "platform":2},
        "BPL":  {"arr":"02:15","dep":"02:25","halt":10,"platform":3},
        "NGP":  {"arr":"06:30","dep":"06:40","halt":10,"platform":1},
        "SC":   {"arr":"11:30","dep":"11:35","halt":5, "platform":5},
        "SBC":  {"arr":"14:40","platform":2},
    },
    "12627": {
        "NDLS": {"dep":"22:30","platform":1},
        "AGC":  {"arr":"00:33","dep":"00:35","halt":2, "platform":1},
        "BPL":  {"arr":"05:30","dep":"05:40","halt":10,"platform":4},
        "NGP":  {"arr":"10:05","dep":"10:15","halt":10,"platform":2},
        "SC":   {"arr":"15:30","dep":"15:45","halt":15,"platform":3},
        "MAS":  {"arr":"21:30","dep":"21:45","halt":15,"platform":7},
        "SBC":  {"arr":"06:15","platform":3},
    },
    "12839": {
        "MMCT": {"dep":"21:30","platform":2},
        "PUNE": {"arr":"23:55","dep":"00:10","halt":15,"platform":2},
        "NGP":  {"arr":"08:30","dep":"08:45","halt":15,"platform":3},
        "SC":   {"arr":"13:15","dep":"13:30","halt":15,"platform":6},
        "VSKP": {"arr":"20:45","dep":"21:00","halt":15,"platform":2},
        "HWH":  {"arr":"07:00","platform":6},
    },
}

STATION_NAMES = {
    "NDLS":"New Delhi","MMCT":"Mumbai Central","MAS":"Chennai Central",
    "HWH":"Howrah Junction","SC":"Secunderabad","AGC":"Agra Cantt",
    "BPL":"Bhopal Junction","NGP":"Nagpur Junction","PUNE":"Pune Junction",
    "VSKP":"Visakhapatnam","SBC":"Bangalore City","ALD":"Prayagraj Jn",
    "KOTA":"Kota Junction",
}

def load_state():
    try:
        with open(STATE_FILE) as f: return json.load(f)
    except: return {}

def load_alerts():
    try:
        with open(ALERTS_FILE) as f: return json.load(f)
    except: return []

def delay_class(d):
    if d < 2:  return "on-time"
    if d < 15: return "delayed"
    return "late"

def delay_str(d):
    if d < 2:   return "ON TIME"
    if d < 15:  return f"+{d:.0f}m"
    return f"<span class='blink'>+{d:.0f}m LATE</span>"

# ── Load data ──────────────────────────────────────────────────────────────────
trains  = load_state()
alerts  = load_alerts()

# Build delay lookup
train_delays = {tid: t.get("delay_minutes", 0) for tid, t in trains.items()}

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("## 📋 Live Schedule Board — NTES Style")
c1, c2, c3 = st.columns([3,1,1])
with c1:
    st.markdown(f'<span style="color:#1a4070;font-family:Share Tech Mono;font-size:14px;">'
                f'IST {datetime.now().strftime("%d %b %Y  %H:%M:%S")}</span>',
                unsafe_allow_html=True)
with c2:
    view = st.radio("View", ["By Station","By Train"], horizontal=True, label_visibility="collapsed")
with c3:
    st.markdown(f'<div style="text-align:right;">'
                f'<span style="color:#3060a0;font-size:12px;">{len([a for a in alerts if a.get("severity")=="HIGH"])} critical alerts</span>'
                f'</div>', unsafe_allow_html=True)

st.divider()

# ═══════════════════════════════════════════════════════
# VIEW 1: BY STATION
# ═══════════════════════════════════════════════════════
if view == "By Station":
    # Get all stations that appear in the schedule
    all_stations = sorted({
        sid
        for sched in FULL_SCHEDULE.values()
        for sid in sched.keys()
    })

    selected_station = st.selectbox(
        "Select Station",
        all_stations,
        format_func=lambda x: f"{x} — {STATION_NAMES.get(x, x)}"
    )

    st.markdown(f"""
    <div class="board-header">
      <div style="font-size:20px;font-weight:700;color:#c8d8f8;font-family:'Share Tech Mono';">
        🚉 {selected_station} &nbsp;·&nbsp; {STATION_NAMES.get(selected_station,'')}
      </div>
      <div style="font-size:12px;color:#1a4070;font-family:'Share Tech Mono';">
        DEPARTURES &amp; ARRIVALS
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Column headers
    st.markdown("""
    <div class="board-row" style="background:#020609;border-color:#0a2040;">
      <div class="col-head">TRAIN</div>
      <div class="col-head">NAME</div>
      <div class="col-head">TYPE</div>
      <div class="col-head">SCHED ARR</div>
      <div class="col-head">ACT ARR</div>
      <div class="col-head">SCHED DEP</div>
      <div class="col-head">PLATFORM</div>
      <div class="col-head">STATUS</div>
    </div>
    """, unsafe_allow_html=True)

    found = False
    for tid, sched in FULL_SCHEDULE.items():
        if selected_station not in sched:
            continue
        found = True
        s    = sched[selected_station]
        d    = train_delays.get(tid, 0)
        dc   = delay_class(d)
        ds   = delay_str(d)
        tc   = TRAIN_COLORS.get(tid, "#448aff")
        tname = TRAIN_NAMES.get(tid, tid)
        ttype = trains.get(tid, {}).get("train_type", "Express")

        sched_arr = s.get("arr", "–")
        sched_dep = s.get("dep", "–")
        platform  = s.get("platform", "–")

        # Compute actual arrival
        if sched_arr != "–":
            h, m = map(int, sched_arr.split(":"))
            act = (datetime.now().replace(hour=h, minute=m, second=0)
                   + timedelta(minutes=d))
            act_arr = act.strftime("%H:%M")
        else:
            act_arr = "–"

        # Train status relative to this station
        t_live = trains.get(tid, {})
        if t_live.get("at_station") and t_live.get("current_station") == selected_station:
            status_html = f'<span style="color:#00e676;font-weight:700;">● AT PLATFORM</span>'
        elif t_live.get("current_station") == selected_station and not t_live.get("at_station"):
            status_html = f'<span style="color:#448aff;">Departed</span>'
        elif t_live.get("next_station") == selected_station:
            status_html = f'<span class="{dc}">{ds} · Approaching</span>'
        else:
            status_html = f'<span class="{dc}">{ds}</span>'

        type_color = {"Rajdhani":"#E63946","Superfast":"#FF9800","Mail/Express":"#00BCD4"}.get(ttype,"#448aff")

        st.markdown(f"""
        <div class="board-row">
          <div style="color:{tc};font-weight:700;">{tid}</div>
          <div style="color:#c8d8f8;">{tname}</div>
          <div><span class="train-pill" style="background:{type_color}22;color:{type_color};">{ttype}</span></div>
          <div style="color:#7090c0;">{sched_arr}</div>
          <div class="{dc}">{act_arr}</div>
          <div style="color:#7090c0;">{sched_dep}</div>
          <div style="color:#ff9100;font-weight:700;">PF {platform}</div>
          <div>{status_html}</div>
        </div>
        """, unsafe_allow_html=True)

    if not found:
        st.info(f"No trains scheduled at {selected_station}")

# ═══════════════════════════════════════════════════════
# VIEW 2: BY TRAIN
# ═══════════════════════════════════════════════════════
else:
    selected_train = st.selectbox(
        "Select Train",
        list(FULL_SCHEDULE.keys()),
        format_func=lambda x: f"{x} — {TRAIN_NAMES.get(x,'')}"
    )

    t_live  = trains.get(selected_train, {})
    t_delay = train_delays.get(selected_train, 0)
    t_color = TRAIN_COLORS.get(selected_train, "#448aff")
    t_name  = TRAIN_NAMES.get(selected_train, "")

    # Train header card
    st.markdown(f"""
    <div style="background:#0d1b2e;border:1px solid #1a3060;border-left:5px solid {t_color};
         border-radius:6px;padding:16px 20px;margin-bottom:16px;">
      <div style="font-size:13px;color:#3060a0;font-family:'Share Tech Mono';">#{selected_train}</div>
      <div style="font-size:24px;font-weight:700;color:#e8f0fe;">{t_name}</div>
      <div style="display:flex;gap:24px;margin-top:8px;font-size:14px;">
        <span style="color:#7090c0;">Type: <b style="color:#c8d8f8;">{t_live.get('train_type','–')}</b></span>
        <span style="color:#7090c0;">Priority: <b style="color:#c8d8f8;">P{t_live.get('priority','–')}</b></span>
        <span style="color:#7090c0;">Delay: <b style="color:{'#ff1744' if t_delay>15 else '#ff9100' if t_delay>5 else '#00e676'};">{t_delay:.1f} min</b></span>
        <span style="color:#7090c0;">Speed: <b style="color:#448aff;">{t_live.get('speed_kmh',0):.0f} km/h</b></span>
        <span style="color:#7090c0;">Weather: <b style="color:#c8d8f8;">{t_live.get('weather','–')}</b></span>
        <span style="color:#7090c0;">Signal: <b style="color:{'#00e676' if t_live.get('signal_status')=='Green' else '#ffea00' if t_live.get('signal_status')=='Yellow' else '#ff1744'};">{t_live.get('signal_status','–')}</b></span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Column headers
    st.markdown("""
    <div class="board-row" style="background:#020609;border-color:#0a2040;">
      <div class="col-head">STATION</div>
      <div class="col-head" style="grid-column:2/4;">STATION NAME</div>
      <div class="col-head">SCHED ARR</div>
      <div class="col-head">ACT ARR</div>
      <div class="col-head">SCHED DEP</div>
      <div class="col-head">HALT</div>
      <div class="col-head">PLATFORM</div>
      <div class="col-head">STATUS</div>
    </div>
    """, unsafe_allow_html=True)

    sched = FULL_SCHEDULE.get(selected_train, {})
    for stop_idx, (sid, s) in enumerate(sched.items()):
        sname    = STATION_NAMES.get(sid, sid)
        sched_arr = s.get("arr", "–")
        sched_dep = s.get("dep", "–")
        platform  = s.get("platform", "–")
        halt      = s.get("halt", "–")

        if sched_arr != "–":
            h, m = map(int, sched_arr.split(":"))
            act = (datetime.now().replace(hour=h, minute=m, second=0)
                   + timedelta(minutes=t_delay))
            act_arr = f'<span class="{delay_class(t_delay)}">{act.strftime("%H:%M")}</span>'
        else:
            act_arr = "–"

        # Determine row highlight
        is_current = (t_live.get("current_station") == sid)
        is_next    = (t_live.get("next_station") == sid)
        is_done    = stop_idx < list(sched.keys()).index(t_live.get("current_station", list(sched.keys())[0])) if t_live else False

        row_bg = ""
        if is_current and t_live.get("at_station"):
            row_bg = "background:#0a2518;border-color:#00e676;"
            status_icon = "🟢 AT PLATFORM"
        elif is_current:
            row_bg = "background:#0a1830;"
            status_icon = "🔵 Departed"
        elif is_next:
            row_bg = "background:#0d1a10;"
            status_icon = "🟡 Next Stop"
        elif is_done:
            row_bg = "opacity:0.5;"
            status_icon = "✓ Done"
        else:
            status_icon = "⏳ Upcoming"

        st.markdown(f"""
        <div class="board-row" style="{row_bg}">
          <div style="color:{t_color};font-weight:700;font-family:'Share Tech Mono';">{sid}</div>
          <div style="color:#c8d8f8;grid-column:2/4;">{sname}</div>
          <div style="color:#7090c0;">{sched_arr}</div>
          <div>{act_arr}</div>
          <div style="color:#7090c0;">{sched_dep}</div>
          <div style="color:#5a7aaa;">{f'{halt}m' if halt != '–' else '–'}</div>
          <div style="color:#ff9100;font-weight:700;">PF {platform}</div>
          <div style="color:#c8d8f8;font-size:12px;">{status_icon}</div>
        </div>
        """, unsafe_allow_html=True)

# ── Alert ticker at bottom ─────────────────────────────────────────────────────
if alerts:
    st.divider()
    st.markdown("**⚠️ Active Alerts**")
    ticker_items = " &nbsp;&nbsp;&nbsp;·&nbsp;&nbsp;&nbsp; ".join(
        f"{'🔴' if a['severity']=='HIGH' else '🟡'} {a['message']}"
        for a in alerts[:8]
    )
    st.markdown(f"""
    <div style="background:#0d0800;border:1px solid #3a2000;border-radius:4px;
         padding:10px 16px;font-size:13px;color:#ff9100;font-family:'Share Tech Mono';
         overflow:hidden;white-space:nowrap;">
      {ticker_items}
    </div>""", unsafe_allow_html=True)

# Auto-refresh
import time
time.sleep(3)
st.rerun()
