"""
Train Schedule Optimiser
Reads live state and generates optimisation recommendations
"""

import json
import os
import time
from datetime import datetime

DATA_DIR   = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
STATE_FILE = os.path.join(DATA_DIR, "live_state.json")
OPT_FILE   = os.path.join(DATA_DIR, "optimisations.json")


PRIORITY_WEIGHT = {1: 1.5, 2: 1.2, 3: 1.0}   # Rajdhani gets more weight

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def recommend_halt_reduction(train):
    """If a high-priority train is delayed, shave halt times."""
    delay = train["delay_minutes"]
    ttype = train["train_type"]
    recs  = []
    if delay > 5 and ttype in ("Rajdhani",):
        reduction = min(delay * 0.4, 3)
        recs.append({
            "action": "REDUCE_HALT",
            "train": train["train_id"],
            "station": train["next_station"],
            "recommendation": f"Reduce halt at {train['next_station_name']} by {reduction:.1f} min",
            "expected_gain_min": round(reduction, 1),
        })
    return recs


def recommend_track_upgrade(train):
    recs = []
    if train.get("track_condition") == "Fair" and train["delay_minutes"] > 3:
        seg = f"{train['current_station']}-{train['next_station']}"
        recs.append({
            "action": "TRACK_MAINTENANCE",
            "segment": seg,
            "recommendation": f"Upgrade track on {seg} from Fair → Good (saves ~5 min/pass)",
            "expected_gain_min": 5.0,
        })
    return recs


def recommend_signal_priority(train):
    recs = []
    if train["signal_status"] != "Green" and train["priority"] == 1:
        recs.append({
            "action": "SIGNAL_PRIORITY",
            "train": train["train_id"],
            "recommendation": f"Grant green corridor for {train['train_name']} ({train['signal_status']} signal detected)",
            "expected_gain_min": 3.0,
        })
    return recs


def recommend_reroute(trains):
    """If multiple trains share a congested segment, suggest spacing."""
    segment_trains = {}
    for t in trains.values():
        seg = f"{t['current_station']}-{t['next_station']}"
        segment_trains.setdefault(seg, []).append(t)
    recs = []
    for seg, tlist in segment_trains.items():
        if len(tlist) >= 2:
            names = ", ".join(t["train_name"] for t in tlist)
            recs.append({
                "action": "SPACING",
                "segment": seg,
                "recommendation": f"Space trains on {seg}: {names} — maintain 10 min headway",
                "expected_gain_min": 4.0,
            })
    return recs


def optimise(state):
    all_recs = []
    for t in state.values():
        all_recs += recommend_halt_reduction(t)
        all_recs += recommend_track_upgrade(t)
        all_recs += recommend_signal_priority(t)
    all_recs += recommend_reroute(state)

    # Score by priority weight * expected gain
    for r in all_recs:
        tid = r.get("train")
        pw  = PRIORITY_WEIGHT.get(state.get(tid or "", {}).get("priority", 3), 1.0)
        r["score"] = round(r["expected_gain_min"] * pw, 2)

    all_recs.sort(key=lambda x: -x["score"])

    total_gain = sum(r["expected_gain_min"] for r in all_recs)
    return {
        "generated_at": datetime.now().isoformat(),
        "total_trains": len(state),
        "avg_delay_min": round(
            sum(t["delay_minutes"] for t in state.values()) / max(len(state), 1), 1
        ),
        "estimated_total_gain_min": round(total_gain, 1),
        "recommendations": all_recs[:10],
    }


def main():
    print("[Optimiser] Starting continuous optimisation loop...")
    while True:
        state = load_state()
        if state:
            result = optimise(state)
            with open(OPT_FILE, "w") as f:
                json.dump(result, f, indent=2)
            print(f"[Optimiser] {len(result['recommendations'])} recommendations | "
                  f"Est. gain: {result['estimated_total_gain_min']} min | "
                  f"Avg delay: {result['avg_delay_min']} min")
        time.sleep(5)


if __name__ == "__main__":
    main()
