"""
Data Export Utility
Exports live Kafka stream data to CSV / JSON files for ML / offline analysis.
Run standalone: python consumer/exporter.py --format csv --duration 60
"""

import json
import os
import csv
import argparse
import time
import signal
import sys
from datetime import datetime
from kafka import KafkaConsumer

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
BASE = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
EXPORT_DIR = os.path.join(BASE, "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

FIELDS = [
    "timestamp","train_id","train_name","train_type","priority",
    "status","current_station","next_station","progress_pct",
    "speed_kmh","odometer_km","delay_minutes",
    "scheduled_arrival","actual_arrival","scheduled_departure",
    "platform","halt_time_min","weather","signal_status",
    "track_type","track_condition","num_tracks","speed_limit_kmh",
    "congestion_pct","passengers","engine_health_pct","at_station",
]

running = True
def handle_sigterm(*_):
    global running
    running = False
    print("\n[Exporter] Shutting down...")
signal.signal(signal.SIGINT, handle_sigterm)
signal.signal(signal.SIGTERM, handle_sigterm)


def export_stream(fmt="csv", duration=None, max_rows=None):
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    outfile  = os.path.join(EXPORT_DIR, f"train_telemetry_{ts}.{fmt}")
    
    consumer = KafkaConsumer(
        "train_events",
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=f"exporter-{ts}",
        auto_offset_reset="latest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        consumer_timeout_ms=10000,
    )

    start  = time.time()
    count  = 0
    rows   = []

    print(f"[Exporter] Writing {fmt.upper()} → {outfile}")
    print(f"[Exporter] Duration: {'unlimited' if not duration else f'{duration}s'} | "
          f"Max rows: {'unlimited' if not max_rows else max_rows}")

    for msg in consumer:
        if not running:
            break
        if duration and (time.time() - start) > duration:
            break
        if max_rows and count >= max_rows:
            break

        data = msg.value
        row  = {f: data.get(f, "") for f in FIELDS}
        rows.append(row)
        count += 1

        if count % 100 == 0:
            elapsed = time.time() - start
            print(f"[Exporter] {count} rows | {elapsed:.0f}s elapsed | "
                  f"{count/elapsed:.1f} msg/s")

    consumer.close()

    if fmt == "csv":
        with open(outfile, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
    else:
        with open(outfile, "w") as f:
            json.dump(rows, f, indent=2, default=str)

    print(f"[Exporter] ✓ Exported {count} rows → {outfile}")
    return outfile, count


def export_snapshot():
    """Export current live state as a single JSON snapshot."""
    state_path = os.path.join(BASE, "live_state.json")
    hist_path  = os.path.join(BASE, "history.json")
    ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
    out        = os.path.join(EXPORT_DIR, f"snapshot_{ts}.json")
    bundle = {}
    for name, path in [("live_state", state_path), ("history", hist_path)]:
        try:
            with open(path) as f:
                bundle[name] = json.load(f)
        except:
            bundle[name] = {}
    bundle["exported_at"] = datetime.now().isoformat()
    with open(out, "w") as f:
        json.dump(bundle, f, indent=2)
    print(f"[Exporter] ✓ Snapshot → {out}")
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TrainOps Data Exporter")
    parser.add_argument("--format",   choices=["csv","json"], default="csv")
    parser.add_argument("--duration", type=int,  default=None, help="Seconds to collect")
    parser.add_argument("--rows",     type=int,  default=None, help="Max rows to export")
    parser.add_argument("--snapshot", action="store_true",    help="Export current state snapshot only")
    args = parser.parse_args()

    if args.snapshot:
        export_snapshot()
    else:
        export_stream(fmt=args.format, duration=args.duration, max_rows=args.rows)
