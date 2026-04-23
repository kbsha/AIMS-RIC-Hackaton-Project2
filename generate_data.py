"""
T2.3 · Grid Outage Forecaster + Appliance Prioritizer
Data Generator — reproducible synthetic dataset
Run: python generate_data.py
Outputs: grid_history.csv, appliances.json, businesses.json
"""

import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta

SEED = 42
np.random.seed(SEED)

# ── 1. GRID HISTORY ──────────────────────────────────────────────────────────

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def generate_grid_history(days=180, seed=SEED):
    np.random.seed(seed)
    start = datetime(2024, 1, 1, 0, 0)
    records = []

    for d in range(days):
        date = start + timedelta(days=d)
        week = d // 7
        # Rainy season: Apr-May, Oct-Nov (months 4,5,10,11)
        month = date.month
        rainy = month in [4, 5, 10, 11]

        for h in range(24):
            ts = date + timedelta(hours=h)

            # Load: two peaks (morning ~8, evening ~19), weekly seasonality
            morning_peak = 80 * np.exp(-0.5 * ((h - 8) / 2.5) ** 2)
            evening_peak = 100 * np.exp(-0.5 * ((h - 19) / 2.0) ** 2)
            base_load = 40
            weekday_boost = 15 if date.weekday() < 5 else -10
            rainy_noise = np.random.normal(0, 12 if rainy else 4)
            load_mw = max(10, base_load + morning_peak + evening_peak +
                         weekday_boost + rainy_noise)

            # Weather
            temp_c = 22 + 6 * np.sin(2 * np.pi * (h - 14) / 24) + \
                     np.random.normal(0, 1.5) + (3 if rainy else 0)
            humidity = 60 + (20 if rainy else 0) + 10 * np.sin(2 * np.pi * h / 24) + \
                       np.random.normal(0, 5)
            humidity = np.clip(humidity, 30, 99)
            wind_ms = max(0, np.random.exponential(3) + (2 if rainy else 0))
            rain_mm = np.random.exponential(3) if (rainy and np.random.rand() < 0.4) else 0.0

            # Outage probability: logistic model
            load_lag1 = load_mw * (1 + np.random.normal(0, 0.02))  # approx lag
            a0, a1, a2, a3 = -3.5, 0.015, 0.08, 0.04
            log_odds = a0 + a1 * load_lag1 + a2 * rain_mm + a3 * (1 if h in range(7, 22) else 0)
            p_outage = sigmoid(log_odds)
            p_outage = np.clip(p_outage + (0.02 if rainy else 0), 0.01, 0.35)
            outage = int(np.random.rand() < p_outage)

            # Duration: LogNormal if outage
            duration_min = 0
            if outage:
                duration_min = int(np.random.lognormal(mean=np.log(90), sigma=0.6))
                duration_min = max(5, min(duration_min, 480))

            records.append({
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "load_mw": round(load_mw, 2),
                "temp_c": round(temp_c, 2),
                "humidity": round(humidity, 2),
                "wind_ms": round(wind_ms, 2),
                "rain_mm": round(rain_mm, 2),
                "outage": outage,
                "duration_min": duration_min,
            })

    df = pd.DataFrame(records)
    df.to_csv("grid_history.csv", index=False)
    print(f"✓ grid_history.csv  {len(df)} rows  outage_rate={df.outage.mean():.3f}")
    return df


# ── 2. APPLIANCES ─────────────────────────────────────────────────────────────

APPLIANCES = [
    {"id": "fridge",       "name": "Commercial Refrigerator", "category": "critical",
     "watts_avg": 350,  "start_up_spike_w": 700,  "revenue_if_running_rwf_per_h": 2500},
    {"id": "hair_dryer",   "name": "Hair Dryer (2×)",         "category": "critical",
     "watts_avg": 2400, "start_up_spike_w": 2500, "revenue_if_running_rwf_per_h": 3000},
    {"id": "clippers",     "name": "Electric Clippers (3×)",  "category": "critical",
     "watts_avg": 120,  "start_up_spike_w": 150,  "revenue_if_running_rwf_per_h": 2000},
    {"id": "water_pump",   "name": "Water Pump",              "category": "critical",
     "watts_avg": 750,  "start_up_spike_w": 1500, "revenue_if_running_rwf_per_h": 1500},
    {"id": "lights",       "name": "LED Lights",              "category": "critical",
     "watts_avg": 80,   "start_up_spike_w": 80,   "revenue_if_running_rwf_per_h": 1000},
    {"id": "air_con",      "name": "Air Conditioner",         "category": "comfort",
     "watts_avg": 1500, "start_up_spike_w": 3000, "revenue_if_running_rwf_per_h": 800},
    {"id": "fan",          "name": "Standing Fan",            "category": "comfort",
     "watts_avg": 75,   "start_up_spike_w": 80,   "revenue_if_running_rwf_per_h": 400},
    {"id": "tv",           "name": "TV / Display Screen",     "category": "comfort",
     "watts_avg": 150,  "start_up_spike_w": 160,  "revenue_if_running_rwf_per_h": 200},
    {"id": "music",        "name": "Music System",            "category": "luxury",
     "watts_avg": 200,  "start_up_spike_w": 220,  "revenue_if_running_rwf_per_h": 100},
    {"id": "neon_sign",    "name": "Neon Sign",               "category": "luxury",
     "watts_avg": 60,   "start_up_spike_w": 65,   "revenue_if_running_rwf_per_h": 50},
]

# ── 3. BUSINESSES ─────────────────────────────────────────────────────────────

BUSINESSES = [
    {
        "id": "salon",
        "name": "Beauty Salon (Kigali)",
        "archetype": "salon",
        "description": "4-chair salon, open 07:00–20:00, 6 days/week",
        "generator_kva": 2.0,
        "appliance_ids": ["hair_dryer", "clippers", "lights", "fan", "tv", "music", "neon_sign"],
        "peak_hours": [8, 9, 10, 15, 16, 17, 18],
        "monthly_revenue_rwf": 1_800_000,
    },
    {
        "id": "cold_room",
        "name": "Cold Room / Butchery",
        "archetype": "cold_room",
        "description": "Meat storage + retail, 05:00–22:00, 7 days",
        "generator_kva": 3.5,
        "appliance_ids": ["fridge", "lights", "water_pump", "fan", "tv"],
        "peak_hours": [5, 6, 7, 17, 18, 19, 20],
        "monthly_revenue_rwf": 2_500_000,
    },
    {
        "id": "tailor",
        "name": "Tailor Shop",
        "archetype": "tailor",
        "description": "3 sewing machines + ironing, 08:00–18:00, 6 days",
        "generator_kva": 1.5,
        "appliance_ids": ["lights", "fan", "music", "tv"],
        "peak_hours": [9, 10, 11, 14, 15, 16],
        "monthly_revenue_rwf": 900_000,
    },
]


def generate_appliance_files():
    with open("appliances.json", "w") as f:
        json.dump(APPLIANCES, f, indent=2)
    print(f"✓ appliances.json  {len(APPLIANCES)} appliances")

    with open("businesses.json", "w") as f:
        json.dump(BUSINESSES, f, indent=2)
    print(f"✓ businesses.json  {len(BUSINESSES)} businesses")


if __name__ == "__main__":
    generate_grid_history()
    generate_appliance_files()
    print("\nAll data files generated successfully.")
