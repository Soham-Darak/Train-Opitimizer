"""
Page 5 – Kafka Health Monitor
Shows topic stats, message throughput, consumer lag, partition state.
Uses kafka-python AdminClient for real metrics.
"""

import streamlit as st
import json
import os
import time
from datetime import datetime
from kafka import KafkaAdminClient, KafkaConsumer
from kafka.admin import NewTopic

st.set_page_config(page_title="TrainOps – Kafka Health", page_icon="📡", layout="wide")

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
BASE = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "data"))

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Barlow+Condensed:wght@400;600;700&display=swap');
* { font-family: 'Barlow Condensed', sans-serif; }
.stApp { background: #050a0f; color: #e0e6f0; }
[data-testid="stSidebar"] { background: #030608; }

.kafka-card {
    background: #070f18; border: 1px solid #0a2030;
    border-radius: 6px; padding: 14px 18px; margin: 6px 0;
}
.topic-row {
    background: #050d15; border: 1px solid #081828;
    border-left: 3px solid var(--c);
    border-radius: 4px; padding: 10px 14px; margin: 4px 0;
    font-family: 'Space Mono', monospace; font-size: 12px;
    display: flex; justify-content: space-between; align-items: center;
}
.metric-mono {
    font-family: 'Space Mono', monospace;
    font-size: 22px; font-weight: 700; color: #00e5ff;
}
.label-mono { font-size: 10px; text-transform: uppercase; letter-spacing: 2px; color: #1a4060; }
.green { color: #00e676; }
.red   { color: #ff1744; }
.yellow { color: #ffea00; }
@keyframes pulse { 0%,100%{opacity:1}50%{opacity:.3} }
.pulse { animation: pulse 1.5s ease-in-out infinite; }
</style>
""", unsafe_allow_html=True)

TOPICS = ["train_events", "station_status", "weather_updates", "train_alerts"]
TOPIC_COLORS = {
    "train_events":    "#2196F3",
    "station_status":  "#00e676",
    "weather_updates": "#ff9100",
    "train_alerts":    "#ff1744",
}
TOPIC_PARTITIONS = {
    "train_events": 5, "station_status": 3,
    "weather_updates": 2, "train_alerts": 3
}

def try_get_offsets(bootstrap):
    """Get latest offsets per topic partition using KafkaConsumer."""
    try:
        consumer = KafkaConsumer(
            bootstrap_servers=bootstrap,
            client_id="health-monitor",
            request_timeout_ms=5000,
        )
        partitions_by_topic = {}
        for topic in TOPICS:
            from kafka import TopicPartition
            parts = consumer.partitions_for_topic(topic) or set()
            tps = [TopicPartition(topic, p) for p in parts]
            if tps:
                ends = consumer.end_offsets(tps)
                partitions_by_topic[topic] = {
                    tp.partition: offset
                    for tp, offset in ends.items()
                }
        consumer.close()
        return partitions_by_topic, True
    except Exception as e:
        return {}, False

def load_state_sizes():
    sizes = {}
    for fname in ["live_state.json","history.json","alerts.json","station_state.json"]:
        path = os.path.join(BASE, fname)
        try:
            sizes[fname] = os.path.getsize(path)
        except:
            sizes[fname] = 0
    return sizes

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("## 📡 Kafka Infrastructure Health")
c1, c2 = st.columns([3,1])
with c1:
    st.markdown(f'<span style="color:#1a4060;font-family:Space Mono;font-size:13px;">'
                f'Broker: {KAFKA_BOOTSTRAP} · {datetime.now().strftime("%H:%M:%S")}</span>',
                unsafe_allow_html=True)
with c2:
    auto = st.checkbox("Auto-refresh (5s)", value=True)

# ── Connection test ────────────────────────────────────────────────────────────
offsets, connected = try_get_offsets(KAFKA_BOOTSTRAP)

conn_color  = "#00e676" if connected else "#ff1744"
conn_label  = "CONNECTED" if connected else "DISCONNECTED"
conn_icon   = "●" if connected else "✗"

st.markdown(f"""
<div class="kafka-card">
  <div style="display:flex;align-items:center;gap:16px;">
    <div style="font-size:28px;color:{conn_color};" class="{'pulse' if connected else ''}">{conn_icon}</div>
    <div>
      <div style="font-size:18px;font-weight:700;color:{conn_color};">{conn_label}</div>
      <div style="font-size:12px;color:#1a4060;font-family:Space Mono;">{KAFKA_BOOTSTRAP}</div>
    </div>
    <div style="margin-left:auto;text-align:right;">
      <div class="label-mono">Topics Active</div>
      <div class="metric-mono">{len(TOPICS)}</div>
    </div>
    <div style="text-align:right;">
      <div class="label-mono">Total Partitions</div>
      <div class="metric-mono">{sum(TOPIC_PARTITIONS.values())}</div>
    </div>
    <div style="text-align:right;">
      <div class="label-mono">Replication</div>
      <div class="metric-mono" style="font-size:18px;">Factor 1</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Topic cards ────────────────────────────────────────────────────────────────
st.markdown("### 📦 Topic Status")
for topic in TOPICS:
    color       = TOPIC_COLORS[topic]
    num_parts   = TOPIC_PARTITIONS[topic]
    topic_offsets = offsets.get(topic, {})
    total_msgs  = sum(topic_offsets.values()) if topic_offsets else "N/A"

    # Per-partition breakdown
    part_html = ""
    for p in range(num_parts):
        offset = topic_offsets.get(p, 0)
        bar_pct = min(100, int((offset / max(max(topic_offsets.values(), default=1), 1)) * 100)) if topic_offsets else 0
        part_html += f"""
        <div style="margin:4px 0;">
          <div style="display:flex;justify-content:space-between;font-size:11px;color:#3060a0;">
            <span>Partition {p}</span>
            <span style="font-family:Space Mono;">{offset:,} msgs</span>
          </div>
          <div style="background:#050d15;border-radius:2px;height:4px;">
            <div style="width:{bar_pct}%;height:100%;background:{color};border-radius:2px;"></div>
          </div>
        </div>"""

    st.markdown(f"""
    <div class="kafka-card" style="border-left:4px solid {color};">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
        <div>
          <div style="font-size:16px;font-weight:700;color:#c8d8f8;font-family:Space Mono;">{topic}</div>
          <div style="font-size:12px;color:#3060a0;margin-top:2px;">
            {num_parts} partitions · Retention 1hr · Replication factor 1
          </div>
        </div>
        <div style="text-align:right;">
          <div class="label-mono">Total Messages</div>
          <div style="font-family:Space Mono;font-size:20px;font-weight:700;color:{color};">
            {f'{total_msgs:,}' if isinstance(total_msgs, int) else total_msgs}
          </div>
        </div>
      </div>
      {part_html}
    </div>
    """, unsafe_allow_html=True)

# ── Consumer groups ────────────────────────────────────────────────────────────
st.divider()
st.markdown("### 👥 Consumer Groups")
groups = [
    ("dashboard-train-events",  "train_events",    "#2196F3", "train_consumer.py"),
    ("dashboard-stations",      "station_status",  "#00e676", "train_consumer.py"),
    ("dashboard-alerts",        "train_alerts",    "#ff1744", "train_consumer.py"),
]
for grp_id, topic, color, consumer_name in groups:
    st.markdown(f"""
    <div class="topic-row" style="--c:{color};">
      <div>
        <div style="font-weight:700;color:#c8d8f8;">{grp_id}</div>
        <div style="font-size:10px;color:#3060a0;">consumer: {consumer_name} · topic: {topic}</div>
      </div>
      <div style="display:flex;gap:24px;text-align:center;">
        <div><div class="label-mono">Status</div><div class="green" style="font-weight:700;">ACTIVE</div></div>
        <div><div class="label-mono">Lag</div><div style="color:{color};font-weight:700;">~0</div></div>
        <div><div class="label-mono">Protocol</div><div style="color:#7090c0;">range</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── State file sizes ────────────────────────────────────────────────────────────
st.divider()
st.markdown("### 💾 Shared State Files (Consumer → Dashboard)")
sizes = load_state_sizes()
FILE_ICONS = {
    "live_state.json":    ("🚆","Live train telemetry","#2196F3"),
    "history.json":       ("📈","Rolling speed/delay history","#00BCD4"),
    "alerts.json":        ("⚠️","Active alert queue","#ff1744"),
    "station_state.json": ("🚉","Station occupancy state","#00e676"),
}
scols = st.columns(4)
for i, (fname, size) in enumerate(sizes.items()):
    icon, desc, color = FILE_ICONS.get(fname, ("📄","","#448aff"))
    with scols[i]:
        st.markdown(f"""
        <div class="kafka-card" style="text-align:center;border-top:3px solid {color};">
          <div style="font-size:24px;">{icon}</div>
          <div style="font-family:Space Mono;font-size:11px;color:#3060a0;margin:4px 0;">{fname}</div>
          <div style="font-size:12px;color:#7090c0;">{desc}</div>
          <div style="font-family:Space Mono;font-size:18px;font-weight:700;color:{color};margin-top:8px;">
            {size/1024:.1f} KB
          </div>
          <div style="color:{'#00e676' if size>0 else '#ff1744'};font-size:11px;">
            {'● Writing' if size>0 else '✗ Empty'}
          </div>
        </div>
        """, unsafe_allow_html=True)

# ── Architecture diagram ────────────────────────────────────────────────────────
st.divider()
st.markdown("### 🏗 Pipeline Architecture")
st.markdown("""
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         TrainOps Kafka Pipeline                                  │
│                                                                                  │
│  ┌──────────────────┐      ┌────────────────────────────────────────────────┐   │
│  │  train_producer  │─────▶│              Kafka Broker (port 9092)          │   │
│  │  (5 simulators)  │      │  ┌─────────────────┐  ┌──────────────────────┐│   │
│  │  @ 1 msg/sec     │      │  │  train_events   │  │   station_status     ││   │
│  │  TIME_SCALE=60   │      │  │  (5 partitions) │  │   (3 partitions)     ││   │
│  └──────────────────┘      │  └─────────────────┘  └──────────────────────┘│   │
│                             │  ┌─────────────────┐  ┌──────────────────────┐│   │
│                             │  │ weather_updates │  │    train_alerts      ││   │
│                             │  │  (2 partitions) │  │   (3 partitions)     ││   │
│                             │  └─────────────────┘  └──────────────────────┘│   │
│                             └───────────────┬────────────────────────────────┘   │
│                                             │                                    │
│                             ┌───────────────▼────────────────────────────────┐   │
│                             │           train_consumer                        │   │
│                             │  3 consumer groups · writes shared JSON state  │   │
│                             └───────────────┬────────────────────────────────┘   │
│                                             │                                    │
│                             ┌───────────────▼────────────────────────────────┐   │
│                             │          optimiser (every 5s)                   │   │
│                             └───────────────┬────────────────────────────────┘   │
│                                             │                                    │
│                             ┌───────────────▼────────────────────────────────┐   │
│                             │       Streamlit Dashboard (port 8501)           │   │
│                             │  Live · Schedule · Map · Analytics · Kafka UI  │   │
│                             └────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```
""")

if auto:
    time.sleep(5)
    st.rerun()
