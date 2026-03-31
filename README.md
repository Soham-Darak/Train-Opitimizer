command 1 : 
pip install -r requirements.txt

docker compose up --build

docker compose down

#  Streamlit Dashboard  →  http://localhost:8501
#  Kafka UI             →  http://localhost:8080

<!-- # 🚆 TrainOps Intelligence Platform

Real-time train schedule simulation, monitoring, and optimisation.
- **5 trains** on realistic Indian Railway routes across **15 stations**
- **Kafka** for streaming telemetry at 1 Hz
- **Streamlit** live dashboard with auto-refresh
- **Time compression**: 1 hour of journey = 60 seconds real time

---

## 📁 Folder Structure

```
train_optimizer/
├── data/
│   ├── config.py               ← Stations, trains, routes, track config
│   ├── live_state.json         ← [auto] Latest train snapshots
│   ├── history.json            ← [auto] Rolling speed/delay history
│   ├── alerts.json             ← [auto] Live alerts feed
│   ├── station_state.json      ← [auto] Station occupancy
│   └── optimisations.json      ← [auto] Optimiser output
│
├── producer/
│   └── train_producer.py       ← Kafka producer (simulates 5 trains)
│
├── consumer/
│   ├── train_consumer.py       ← Kafka consumer (writes JSON state)
│   └── optimiser.py            ← Schedule optimisation engine
│
├── dashboard/
│   ├── app.py                  ← Main Streamlit live dashboard
│   └── pages/
│       └── 1_Optimiser.py      ← Optimisation recommendations page
│
├── docker/
│   ├── Dockerfile.producer
│   ├── Dockerfile.consumer
│   └── Dockerfile.dashboard
│
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start (Docker — Recommended)

```bash
# Clone / enter project
cd train_optimizer

# Start everything
docker-compose up --build

# Services:
#  Streamlit Dashboard  →  http://localhost:8501
#  Kafka UI             →  http://localhost:8080
#  Kafka Broker         →  localhost:9092
```

> The first startup takes ~60 seconds as Kafka initialises and topics are created.

---

## 🖥️ Local Dev (without Docker)

### 1. Start Kafka via Docker only
```bash
docker-compose up zookeeper kafka kafka-init kafka-ui
```

### 2. Install Python deps
```bash
pip install -r requirements.txt
```

### 3. Start consumer + optimiser (terminal 1)
```bash
python consumer/train_consumer.py &
python consumer/optimiser.py
```

### 4. Start producer (terminal 2)
```bash
python producer/train_producer.py
```

### 5. Launch dashboard (terminal 3)
```bash
streamlit run dashboard/app.py
```

---

## 📡 Kafka Topics

| Topic            | Purpose                          | Partitions |
|------------------|----------------------------------|------------|
| `train_events`   | Real-time train telemetry (1 Hz) | 5          |
| `station_status` | Arrivals/departures at stations  | 3          |
| `weather_updates`| Weather per station (every 10s)  | 2          |
| `train_alerts`   | Delay/signal/congestion alerts   | 3          |

---

## 🚆 Trains & Routes

| ID    | Name                    | Type        | Priority | Route |
|-------|-------------------------|-------------|----------|-------|
| 12951 | Mumbai Rajdhani Express | Rajdhani    | P1       | NDLS → AGC → KOTA → BPL → MMCT |
| 12301 | Howrah Rajdhani Express | Rajdhani    | P1       | NDLS → ALD → HWH |
| 22691 | Rajdhani Express SBC    | Rajdhani    | P1       | NDLS → AGC → BPL → NGP → SC → SBC |
| 12627 | Karnataka Express       | Superfast   | P2       | NDLS → AGC → BPL → NGP → SC → MAS → SBC |
| 12839 | Howrah Mail             | Mail/Express| P3       | MMCT → PUNE → NGP → SC → VSKP → HWH |

---

## 📊 Dataset Parameters

Each Kafka message on `train_events` contains:

```json
{
  "timestamp":           "2024-01-01T10:30:00",
  "train_id":            "12951",
  "train_name":          "Mumbai Rajdhani Express",
  "train_type":          "Rajdhani",
  "priority":            1,
  "status":              "Departed",
  "current_station":     "AGC",
  "current_station_name":"Agra Cantt",
  "next_station":        "KOTA",
  "next_station_name":   "Kota Junction",
  "progress_pct":        45.3,
  "speed_kmh":           118.4,
  "odometer_km":         312.7,
  "delay_minutes":       7.2,
  "scheduled_arrival":   "21:10",
  "actual_arrival":      "21:17",
  "scheduled_departure": "17:00",
  "platform":            1,
  "halt_time_min":       5,
  "weather":             "Clear",
  "signal_status":       "Green",
  "track_type":          "Electrified",
  "track_condition":     "Good",
  "num_tracks":          2,
  "speed_limit_kmh":     110,
  "congestion_pct":      12,
  "passengers":          1024,
  "engine_health_pct":   97.3,
  "route":               ["AGC","KOTA","BPL","MMCT"],
  "at_station":          false
}
```

---

## ⚙️ Optimisation Strategies

The `optimiser.py` module generates ranked recommendations:

| Action              | Trigger                         | Expected Gain |
|---------------------|---------------------------------|---------------|
| `REDUCE_HALT`       | High-priority train delayed >5m | 1–3 min       |
| `TRACK_MAINTENANCE` | Fair track + delay detected     | ~5 min        |
| `SIGNAL_PRIORITY`   | P1 train on non-green signal    | ~3 min        |
| `SPACING`           | 2+ trains on same segment       | ~4 min        |

---

## ⏱️ Time Compression

```
TIME_SCALE = 60   # 1 real journey hour = 60 wall-clock seconds

Example:
  NDLS → MMCT distance: 1395 km
  At avg speed 90 km/h  → 15.5 real hours
  In simulation        → ~15.5 minutes
```

Halt times are also compressed proportionally. -->
