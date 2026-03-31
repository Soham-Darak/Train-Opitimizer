"""
Train Event Consumer - robust version
Reads from Kafka topics, writes JSON state files for Streamlit dashboard.
"""

import json
import time
import os
import sys
import threading
from datetime import datetime
from collections import defaultdict, deque
from kafka import KafkaConsumer

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DATA_DIR        = os.environ.get("DATA_DIR", "/app/data")
STATE_FILE      = os.path.join(DATA_DIR, "live_state.json")
HISTORY_FILE    = os.path.join(DATA_DIR, "history.json")
ALERTS_FILE     = os.path.join(DATA_DIR, "alerts.json")
STATION_FILE    = os.path.join(DATA_DIR, "station_state.json")

os.makedirs(DATA_DIR, exist_ok=True)
print(f"[Consumer] DATA_DIR={DATA_DIR}")
print(f"[Consumer] STATE_FILE={STATE_FILE}")

train_latest  = {}
history       = defaultdict(lambda: deque(maxlen=120))
alerts        = deque(maxlen=50)
station_state = {}
lock          = threading.Lock()


def save_state():
    try:
        with lock:
            with open(STATE_FILE, "w") as f:
                json.dump(train_latest, f, default=str)
            with open(HISTORY_FILE, "w") as f:
                json.dump({k: list(v) for k, v in history.items()}, f, default=str)
            with open(ALERTS_FILE, "w") as f:
                json.dump(list(alerts), f, default=str)
            with open(STATION_FILE, "w") as f:
                json.dump(station_state, f, default=str)
    except Exception as e:
        print(f"[Consumer] Save error: {e}")


def consume_loop(topics, group_id, handler):
    while True:
        try:
            consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=KAFKA_BOOTSTRAP,
                group_id=group_id,
                auto_offset_reset="latest",
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                enable_auto_commit=True,
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000,
            )
            print(f"[Consumer] Connected: {topics}")
            for msg in consumer:
                try:
                    handler(msg.value)
                except Exception as e:
                    print(f"[Consumer] Handler error: {e}")
        except Exception as e:
            print(f"[Consumer] Connection error ({topics}): {e}. Retrying in 5s...")
            time.sleep(5)


def handle_train(data):
    tid = data.get("train_id")
    if not tid:
        return
    with lock:
        train_latest[tid] = data
        history[tid].append({
            "timestamp":    data["timestamp"],
            "speed_kmh":    data["speed_kmh"],
            "delay_min":    data["delay_minutes"],
            "progress_pct": data["progress_pct"],
            "congestion":   data["congestion_pct"],
            "engine":       data["engine_health_pct"],
            "status":       data["status"],
            "station":      data["current_station"],
        })


def handle_station(data):
    sid = data.get("station_id")
    if not sid:
        return
    with lock:
        station_state[sid] = data


def handle_alert(data):
    with lock:
        alerts.appendleft(data)


def writer_loop():
    while True:
        save_state()
        time.sleep(1)


def wait_for_kafka():
    """Block until Kafka is reachable."""
    from kafka import KafkaAdminClient
    print(f"[Consumer] Waiting for Kafka at {KAFKA_BOOTSTRAP}...")
    for i in range(60):
        try:
            admin = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP,
                                     request_timeout_ms=3000)
            admin.close()
            print(f"[Consumer] Kafka ready after {i*3}s")
            return
        except Exception:
            time.sleep(3)
    print("[Consumer] WARNING: Kafka not reachable after 3 min, continuing anyway...")


def main():
    wait_for_kafka()
    time.sleep(5)  # Extra buffer for producer to start

    threads = [
        threading.Thread(target=consume_loop, args=(["train_events"],   "cg-train",   handle_train),   daemon=True),
        threading.Thread(target=consume_loop, args=(["station_status"], "cg-station", handle_station), daemon=True),
        threading.Thread(target=consume_loop, args=(["train_alerts"],   "cg-alerts",  handle_alert),   daemon=True),
        threading.Thread(target=writer_loop,  daemon=True),
    ]
    for t in threads:
        t.start()

    print("[Consumer] All threads running.")
    while True:
        time.sleep(10)
        with lock:
            print(f"[Consumer] ✓ Trains={len(train_latest)} | Alerts={len(alerts)} | Stations={len(station_state)}")


if __name__ == "__main__":
    main()
