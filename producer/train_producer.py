"""
Train Telemetry Producer
Generates realistic real-time train data compressed in time scale
1 hour of actual journey = 60 seconds simulation time
"""

import json
import time
import random
import math
from datetime import datetime, timedelta
from kafka import KafkaProducer
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.config import (
    STATIONS, TRAINS, TRACK_SEGMENTS, TIME_SCALE,
    WEATHER_CONDITIONS, WEATHER_DELAY_MULTIPLIER
)

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_TRAIN_EVENTS   = "train_events"
TOPIC_STATION_STATUS = "station_status"
TOPIC_WEATHER        = "weather_updates"
TOPIC_ALERTS         = "train_alerts"


class TrainSimulator:
    """
    Simulates a single train on its route.
    Time is compressed: TIME_SCALE seconds = 1 real hour of journey.
    """

    def __init__(self, train_id: str):
        self.train_id = train_id
        cfg = TRAINS[train_id]
        self.name        = cfg["name"]
        self.train_type  = cfg["type"]
        self.priority    = cfg["priority"]
        self.max_speed   = cfg["max_speed_kmh"]
        self.route       = cfg["route"]
        self.sched       = cfg["scheduled_times"]
        self.dist        = cfg["distance_km"]
        self.color       = cfg["color"]

        # Simulation state
        self.sim_start_wall  = time.time()          # wall-clock when sim started
        self.current_seg_idx = 0                    # index into route (which leg)
        self.seg_elapsed_sec = 0.0                  # wall-clock seconds spent on current leg
        self.cumulative_delay_min = 0.0             # accumulated delay in "train minutes"
        self.status      = "Departed"
        self.current_station = self.route[0]
        self.next_station    = self.route[1] if len(self.route) > 1 else self.route[0]
        self.at_station      = False
        self.halt_remaining  = 0.0                  # simulated seconds left at halt
        self.weather         = random.choice(WEATHER_CONDITIONS[:3])
        self.speed_kmh       = 0.0
        self.progress_pct    = 0.0                  # progress on current leg 0-100
        self.odometer_km     = 0.0
        self.passengers      = random.randint(800, 1200)
        self.engine_health   = 100.0
        self.signal_status   = "Green"
        self.platform        = None
        self.last_event_time = datetime.now()

    # ------------------------------------------------------------------ helpers

    def _seg_key(self, a, b):
        k1, k2 = f"{a}-{b}", f"{b}-{a}"
        return k1 if k1 in TRACK_SEGMENTS else (k2 if k2 in TRACK_SEGMENTS else None)

    def _seg_distance(self):
        key = self._seg_key(self.route[self.current_seg_idx],
                            self.route[self.current_seg_idx + 1])
        return self.dist.get(key, self.dist.get(f"{self.route[self.current_seg_idx]}-{self.route[self.current_seg_idx+1]}", 300))

    def _seg_duration_real_hours(self):
        """How many real hours this leg takes (uncompressed)."""
        dist = self._seg_distance()
        speed = self.max_speed * random.uniform(0.70, 0.90)
        return dist / speed

    def _seg_duration_wall_sec(self):
        """Wall-clock seconds this leg should take (compressed)."""
        return self._seg_duration_real_hours() * TIME_SCALE

    def _halt_wall_sec(self, station):
        """Wall-clock seconds for halt at a station."""
        halt_min = self.sched.get(station, {}).get("halt", 2)
        # Each 1 train-minute = TIME_SCALE/60 wall-seconds
        return halt_min * (TIME_SCALE / 60)

    def _apply_delay(self, base_delay_min):
        weather_delay = WEATHER_DELAY_MULTIPLIER.get(self.weather, 0)
        track_key = self._seg_key(self.route[self.current_seg_idx],
                                   self.route[min(self.current_seg_idx+1, len(self.route)-1)])
        track_cond = TRACK_SEGMENTS.get(track_key, {}).get("condition", "Good")
        track_delay = {"Good": 0, "Fair": random.uniform(0, 5), "Poor": random.uniform(5, 15)}.get(track_cond, 0)
        congestion  = random.uniform(0, 3) if random.random() < 0.2 else 0
        self.cumulative_delay_min += base_delay_min + weather_delay + track_delay + congestion
        # Occasionally recover some delay
        if random.random() < 0.15:
            recovery = random.uniform(1, min(5, self.cumulative_delay_min))
            self.cumulative_delay_min = max(0, self.cumulative_delay_min - recovery)

    # ------------------------------------------------------------------ tick

    def tick(self, dt: float):
        """Advance simulation by dt wall-clock seconds."""
        if self.at_station:
            self.halt_remaining -= dt
            self.speed_kmh = 0
            if self.halt_remaining <= 0:
                self.at_station = False
                self.current_seg_idx += 1
                if self.current_seg_idx >= len(self.route) - 1:
                    self.status = "Arrived at Terminus"
                    return
                self.seg_elapsed_sec = 0
                self.current_station = self.route[self.current_seg_idx]
                self.next_station    = self.route[self.current_seg_idx + 1]
                self.status = "Departed"
                self.signal_status = random.choice(["Green", "Green", "Green", "Yellow"])
        else:
            self.seg_elapsed_sec += dt
            seg_dur = self._seg_duration_wall_sec()
            self.progress_pct = min(100.0, (self.seg_elapsed_sec / seg_dur) * 100)

            # Speed model: accelerate → cruise → brake
            if self.progress_pct < 10:
                self.speed_kmh = self.max_speed * (self.progress_pct / 10) * random.uniform(0.9, 1.0)
            elif self.progress_pct > 90:
                self.speed_kmh = self.max_speed * ((100 - self.progress_pct) / 10) * random.uniform(0.9, 1.0)
            else:
                self.speed_kmh = self.max_speed * random.uniform(0.80, 0.95)

            # Track speed limit
            key = self._seg_key(self.route[self.current_seg_idx],
                                 self.route[self.current_seg_idx + 1])
            if key:
                limit = TRACK_SEGMENTS[key]["speed_limit"]
                self.speed_kmh = min(self.speed_kmh, limit)

            dist = self._seg_distance()
            self.odometer_km += (self.speed_kmh * dt) / 3600

            # Signal / congestion events
            if random.random() < 0.02:
                self.signal_status = random.choice(["Red", "Yellow"])
                self._apply_delay(random.uniform(1, 4))
            elif random.random() < 0.05:
                self.signal_status = "Yellow"
            else:
                self.signal_status = "Green"

            # Engine micro-degradation
            self.engine_health -= random.uniform(0, 0.01)
            self.engine_health  = max(85.0, self.engine_health)

            if self.progress_pct >= 100:
                # Arriving at next station
                dest = self.route[self.current_seg_idx + 1]
                self._apply_delay(random.uniform(0, 2))
                self.at_station       = True
                self.current_station  = dest
                self.halt_remaining   = self._halt_wall_sec(dest)
                self.platform         = self.sched.get(dest, {}).get("platform", random.randint(1, 6))
                self.status           = "Arrived"
                self.progress_pct     = 100
                self.speed_kmh        = 0
                # Change weather occasionally
                if random.random() < 0.3:
                    self.weather = random.choice(WEATHER_CONDITIONS)

    # ------------------------------------------------------------------ snapshot

    def snapshot(self) -> dict:
        seg_idx = min(self.current_seg_idx, len(self.route) - 2)
        origin  = self.route[seg_idx]
        dest    = self.route[min(seg_idx + 1, len(self.route) - 1)]
        key     = self._seg_key(origin, dest) or f"{origin}-{dest}"
        track   = TRACK_SEGMENTS.get(key, {"track_type": "Electrified", "tracks": 2,
                                            "speed_limit": 100, "condition": "Good"})

        sched_arr_str = self.sched.get(self.next_station, {}).get("arr", "N/A")
        delay_sec = self.cumulative_delay_min * (TIME_SCALE / 60)
        if sched_arr_str != "N/A":
            h, m = map(int, sched_arr_str.split(":"))
            base = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
            actual_arr = base + timedelta(minutes=self.cumulative_delay_min)
            actual_arr_str = actual_arr.strftime("%H:%M")
        else:
            actual_arr_str = "N/A"

        sched_dep_str = self.sched.get(self.current_station, {}).get("dep",
                        self.sched.get(self.route[0], {}).get("dep", "N/A"))

        congestion_pct = random.randint(5, 30) if self.signal_status == "Green" else random.randint(40, 80)

        return {
            "timestamp":          datetime.now().isoformat(),
            "train_id":           self.train_id,
            "train_name":         self.name,
            "train_type":         self.train_type,
            "priority":           self.priority,
            "color":              self.color,
            "status":             self.status,
            "current_station":    self.current_station,
            "current_station_name": STATIONS[self.current_station]["name"],
            "next_station":       self.next_station,
            "next_station_name":  STATIONS[self.next_station]["name"],
            "progress_pct":       round(self.progress_pct, 1),
            "speed_kmh":          round(self.speed_kmh, 1),
            "odometer_km":        round(self.odometer_km, 1),
            "delay_minutes":      round(self.cumulative_delay_min, 1),
            "scheduled_arrival":  sched_arr_str,
            "actual_arrival":     actual_arr_str,
            "scheduled_departure": sched_dep_str,
            "platform":           self.platform,
            "halt_time_min":      self.sched.get(self.current_station, {}).get("halt", 0),
            "weather":            self.weather,
            "signal_status":      self.signal_status,
            "track_type":         track["track_type"],
            "track_condition":    track["condition"],
            "num_tracks":         track["tracks"],
            "speed_limit_kmh":    track["speed_limit"],
            "congestion_pct":     congestion_pct,
            "passengers":         self.passengers,
            "engine_health_pct":  round(self.engine_health, 1),
            "route":              self.route,
            "at_station":         self.at_station,
        }


def main():
    print(f"[Producer] Connecting to Kafka at {KAFKA_BOOTSTRAP}...")
    for attempt in range(30):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
                retries=3,
            )
            print("[Producer] Connected!")
            break
        except Exception as e:
            print(f"[Producer] Attempt {attempt+1}/30 failed: {e}. Retrying in 3s...")
            time.sleep(3)
    else:
        print("[Producer] Could not connect to Kafka. Exiting.")
        sys.exit(1)

    simulators = {tid: TrainSimulator(tid) for tid in TRAINS}
    tick_interval = 1.0  # produce every second

    print(f"[Producer] Simulating {len(simulators)} trains. TIME_SCALE={TIME_SCALE}s per hour")
    print("[Producer] Producing to topics: train_events, station_status, weather_updates, train_alerts")

    weather_counter = 0

    while True:
        start = time.time()

        for tid, sim in simulators.items():
            sim.tick(tick_interval)
            snap = sim.snapshot()

            # Main train event
            producer.send(TOPIC_TRAIN_EVENTS, snap)

            # Station status when at a station
            if snap["at_station"]:
                producer.send(TOPIC_STATION_STATUS, {
                    "timestamp":     snap["timestamp"],
                    "station_id":    snap["current_station"],
                    "station_name":  snap["current_station_name"],
                    "train_id":      tid,
                    "train_name":    snap["train_name"],
                    "train_type":    snap["train_type"],
                    "platform":      snap["platform"],
                    "status":        snap["status"],
                    "delay_minutes": snap["delay_minutes"],
                    "passengers":    snap["passengers"],
                })

            # Alerts
            if snap["delay_minutes"] > 15:
                producer.send(TOPIC_ALERTS, {
                    "timestamp":   snap["timestamp"],
                    "alert_type":  "MAJOR_DELAY",
                    "severity":    "HIGH",
                    "train_id":    tid,
                    "train_name":  snap["train_name"],
                    "message":     f"{snap['train_name']} is {snap['delay_minutes']:.0f} min late near {snap['current_station_name']}",
                    "delay_min":   snap["delay_minutes"],
                    "cause":       snap["weather"] if snap["weather"] not in ["Clear","Cloudy"] else "Congestion",
                })
            elif snap["delay_minutes"] > 5:
                producer.send(TOPIC_ALERTS, {
                    "timestamp":   snap["timestamp"],
                    "alert_type":  "MINOR_DELAY",
                    "severity":    "MEDIUM",
                    "train_id":    tid,
                    "train_name":  snap["train_name"],
                    "message":     f"{snap['train_name']} is {snap['delay_minutes']:.0f} min late",
                    "delay_min":   snap["delay_minutes"],
                    "cause":       "Signal / Track",
                })

        # Weather broadcast every 10 ticks
        weather_counter += 1
        if weather_counter % 10 == 0:
            for sid, sinfo in STATIONS.items():
                producer.send(TOPIC_WEATHER, {
                    "timestamp":    datetime.now().isoformat(),
                    "station_id":   sid,
                    "station_name": sinfo["name"],
                    "weather":      random.choice(WEATHER_CONDITIONS),
                    "temperature":  round(random.uniform(18, 42), 1),
                    "visibility_km": round(random.uniform(1, 15), 1),
                    "wind_kmh":     round(random.uniform(0, 60), 1),
                })

        producer.flush()
        elapsed = time.time() - start
        sleep_for = max(0, tick_interval - elapsed)
        time.sleep(sleep_for)


if __name__ == "__main__":
    main()
