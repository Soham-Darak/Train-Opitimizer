"""
Train Network Configuration
Real Indian Railway-inspired network with 15 stations and 5 trains
"""

# 15 Stations with coordinates (lat, lng) and zone
STATIONS = {
    "NDLS": {"name": "New Delhi", "lat": 28.6419, "lng": 77.2194, "zone": "NR", "major": True},
    "MMCT": {"name": "Mumbai Central", "lat": 18.9696, "lng": 72.8194, "zone": "WR", "major": True},
    "MAS":  {"name": "Chennai Central", "lat": 13.0827, "lng": 80.2707, "zone": "SR", "major": True},
    "HWH":  {"name": "Howrah Junction", "lat": 22.5839, "lng": 88.3424, "zone": "ER", "major": True},
    "SC":   {"name": "Secunderabad", "lat": 17.4344, "lng": 78.5013, "zone": "SCR", "major": True},
    "AGC":  {"name": "Agra Cantt", "lat": 27.1592, "lng": 78.0082, "zone": "NCR", "major": False},
    "BPL":  {"name": "Bhopal Junction", "lat": 23.2639, "lng": 77.4126, "zone": "WCR", "major": False},
    "NGP":  {"name": "Nagpur Junction", "lat": 21.1458, "lng": 79.0882, "zone": "CR", "major": False},
    "PUNE": {"name": "Pune Junction", "lat": 18.5279, "lng": 73.8742, "zone": "CR", "major": False},
    "JP":   {"name": "Jaipur Junction", "lat": 26.9124, "lng": 75.7873, "zone": "NWR", "major": False},
    "LKO":  {"name": "Lucknow NR", "lat": 26.8467, "lng": 80.9462, "zone": "NR", "major": False},
    "VSKP": {"name": "Visakhapatnam", "lat": 17.6868, "lng": 83.2185, "zone": "ECoR", "major": False},
    "SBC":  {"name": "Bangalore City", "lat": 12.9762, "lng": 77.5993, "zone": "SWR", "major": True},
    "ALD":  {"name": "Prayagraj Jn", "lat": 25.4358, "lng": 81.8463, "zone": "NCR", "major": False},
    "KOTA": {"name": "Kota Junction", "lat": 25.1802, "lng": 75.8333, "zone": "WCR", "major": False},
}

# 5 Train Definitions with routes
TRAINS = {
    "12951": {
        "name": "Mumbai Rajdhani Express",
        "type": "Rajdhani",
        "priority": 1,
        "max_speed_kmh": 130,
        "route": ["NDLS", "AGC", "KOTA", "BPL", "MMCT"],
        "scheduled_times": {
            "NDLS":  {"dep": "17:00"},
            "AGC":   {"arr": "18:45", "dep": "18:47", "halt": 2, "platform": 3},
            "KOTA":  {"arr": "21:10", "dep": "21:15", "halt": 5, "platform": 1},
            "BPL":   {"arr": "23:50", "dep": "00:00", "halt": 10, "platform": 2},
            "MMCT":  {"arr": "07:55"},
        },
        "distance_km": {"NDLS-AGC": 200, "AGC-KOTA": 300, "KOTA-BPL": 270, "BPL-MMCT": 595},
        "color": "#E63946",
    },
    "12301": {
        "name": "Howrah Rajdhani Express",
        "type": "Rajdhani",
        "priority": 1,
        "max_speed_kmh": 130,
        "route": ["NDLS", "ALD", "HWH"],
        "scheduled_times": {
            "NDLS":  {"dep": "16:55"},
            "ALD":   {"arr": "22:20", "dep": "22:25", "halt": 5, "platform": 4},
            "HWH":   {"arr": "10:00"},
        },
        "distance_km": {"NDLS-ALD": 642, "ALD-HWH": 541},
        "color": "#2196F3",
    },
    "22691": {
        "name": "Rajdhani Express SBC",
        "type": "Rajdhani",
        "priority": 1,
        "max_speed_kmh": 120,
        "route": ["NDLS", "AGC", "BPL", "NGP", "SC", "SBC"],
        "scheduled_times": {
            "NDLS":  {"dep": "20:00"},
            "AGC":   {"arr": "21:50", "dep": "21:52", "halt": 2, "platform": 2},
            "BPL":   {"arr": "02:15", "dep": "02:25", "halt": 10, "platform": 3},
            "NGP":   {"arr": "06:30", "dep": "06:40", "halt": 10, "platform": 1},
            "SC":    {"arr": "11:30", "dep": "11:35", "halt": 5, "platform": 5},
            "SBC":   {"arr": "14:40"},
        },
        "distance_km": {"NDLS-AGC": 200, "AGC-BPL": 470, "BPL-NGP": 345, "NGP-SC": 498, "SC-SBC": 574},
        "color": "#FF9800",
    },
    "12627": {
        "name": "Karnataka Express",
        "type": "Superfast",
        "priority": 2,
        "max_speed_kmh": 110,
        "route": ["NDLS", "AGC", "BPL", "NGP", "SC", "MAS", "SBC"],
        "scheduled_times": {
            "NDLS":  {"dep": "22:30"},
            "AGC":   {"arr": "00:33", "dep": "00:35", "halt": 2, "platform": 1},
            "BPL":   {"arr": "05:30", "dep": "05:40", "halt": 10, "platform": 4},
            "NGP":   {"arr": "10:05", "dep": "10:15", "halt": 10, "platform": 2},
            "SC":    {"arr": "15:30", "dep": "15:45", "halt": 15, "platform": 3},
            "MAS":   {"arr": "21:30", "dep": "21:45", "halt": 15, "platform": 7},
            "SBC":   {"arr": "06:15"},
        },
        "distance_km": {"NDLS-AGC": 200, "AGC-BPL": 470, "BPL-NGP": 345, "NGP-SC": 498, "SC-MAS": 792, "MAS-SBC": 362},
        "color": "#9C27B0",
    },
    "12839": {
        "name": "Howrah Mail",
        "type": "Mail/Express",
        "priority": 3,
        "max_speed_kmh": 100,
        "route": ["MMCT", "PUNE", "NGP", "SC", "VSKP", "HWH"],
        "scheduled_times": {
            "MMCT":  {"dep": "21:30"},
            "PUNE":  {"arr": "23:55", "dep": "00:10", "halt": 15, "platform": 2},
            "NGP":   {"arr": "08:30", "dep": "08:45", "halt": 15, "platform": 3},
            "SC":    {"arr": "13:15", "dep": "13:30", "halt": 15, "platform": 6},
            "VSKP":  {"arr": "20:45", "dep": "21:00", "halt": 15, "platform": 2},
            "HWH":   {"arr": "07:00"},
        },
        "distance_km": {"MMCT-PUNE": 192, "PUNE-NGP": 848, "NGP-SC": 498, "SC-VSKP": 700, "VSKP-HWH": 711},
        "color": "#00BCD4",
    },
}

# Track conditions between stations
TRACK_SEGMENTS = {
    "NDLS-AGC":  {"track_type": "Electrified", "tracks": 4, "speed_limit": 130, "condition": "Good"},
    "AGC-KOTA":  {"track_type": "Electrified", "tracks": 2, "speed_limit": 110, "condition": "Good"},
    "KOTA-BPL":  {"track_type": "Electrified", "tracks": 2, "speed_limit": 100, "condition": "Fair"},
    "BPL-MMCT":  {"track_type": "Electrified", "tracks": 2, "speed_limit": 110, "condition": "Good"},
    "NDLS-ALD":  {"track_type": "Electrified", "tracks": 3, "speed_limit": 130, "condition": "Good"},
    "ALD-HWH":   {"track_type": "Electrified", "tracks": 2, "speed_limit": 110, "condition": "Fair"},
    "AGC-BPL":   {"track_type": "Electrified", "tracks": 2, "speed_limit": 110, "condition": "Good"},
    "BPL-NGP":   {"track_type": "Electrified", "tracks": 2, "speed_limit": 100, "condition": "Good"},
    "NGP-SC":    {"track_type": "Electrified", "tracks": 2, "speed_limit": 110, "condition": "Good"},
    "SC-SBC":    {"track_type": "Electrified", "tracks": 2, "speed_limit": 100, "condition": "Fair"},
    "SC-MAS":    {"track_type": "Electrified", "tracks": 2, "speed_limit": 110, "condition": "Good"},
    "MAS-SBC":   {"track_type": "Electrified", "tracks": 2, "speed_limit": 100, "condition": "Good"},
    "MMCT-PUNE": {"track_type": "Electrified", "tracks": 2, "speed_limit": 100, "condition": "Good"},
    "PUNE-NGP":  {"track_type": "Electrified", "tracks": 2, "speed_limit": 100, "condition": "Fair"},
    "SC-VSKP":   {"track_type": "Electrified", "tracks": 2, "speed_limit": 100, "condition": "Good"},
    "VSKP-HWH":  {"track_type": "Electrified", "tracks": 2, "speed_limit": 110, "condition": "Good"},
}

# Simulation time compression: 1 real hour = TIME_SCALE seconds
TIME_SCALE = 60  # 1 hour of train journey = 60 seconds real time

WEATHER_CONDITIONS = ["Clear", "Cloudy", "Fog", "Light Rain", "Heavy Rain", "Storm", "Heatwave"]
WEATHER_DELAY_MULTIPLIER = {
    "Clear": 0, "Cloudy": 0, "Fog": 5, "Light Rain": 2,
    "Heavy Rain": 8, "Storm": 15, "Heatwave": 3
}
