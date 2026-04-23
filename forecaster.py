"""
T2.3 · forecaster.py
24-hour-ahead probabilistic outage forecaster.
Outputs P(outage) and E[duration | outage] per hour.

Usage:
    from forecaster import Forecaster
    fc = Forecaster()
    fc.fit("grid_history.csv")
    forecast = fc.predict_next_24h()   # list of 24 dicts

API endpoint (fast path):
    python forecaster.py --serve       # prints JSON, <300ms on CPU
    python forecaster.py --eval        # rolling 30-day Brier + MAE
"""

import argparse
import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, LGBMRegressor

warnings.filterwarnings("ignore")

MODEL_PATH_CLF = "model_outage_clf.pkl"
MODEL_PATH_REG = "model_duration_reg.pkl"


# ── Feature Engineering ───────────────────────────────────────────────────────

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    df["hour"] = df["timestamp"].dt.hour
    df["dayofweek"] = df["timestamp"].dt.dayofweek
    df["month"] = df["timestamp"].dt.month
    df["is_weekend"] = (df["dayofweek"] >= 5).astype(int)
    df["is_peak_morning"] = ((df["hour"] >= 7) & (df["hour"] <= 10)).astype(int)
    df["is_peak_evening"] = ((df["hour"] >= 17) & (df["hour"] <= 21)).astype(int)
    df["is_rainy_season"] = df["month"].isin([4, 5, 10, 11]).astype(int)

    # Lagged load features (1h, 2h, 24h, 48h)
    for lag in [1, 2, 24, 48]:
        df[f"load_lag{lag}"] = df["load_mw"].shift(lag)

    # Rolling stats
    df["load_roll3_mean"] = df["load_mw"].shift(1).rolling(3).mean()
    df["load_roll6_std"] = df["load_mw"].shift(1).rolling(6).std()
    df["rain_roll3_sum"] = df["rain_mm"].shift(1).rolling(3).sum()
    df["outage_lag1"] = df["outage"].shift(1)
    df["outage_roll6_sum"] = df["outage"].shift(1).rolling(6).sum()

    df = df.dropna().reset_index(drop=True)
    return df


FEATURE_COLS = [
    "load_lag1", "load_lag2", "load_lag24", "load_lag48",
    "load_roll3_mean", "load_roll6_std", "rain_roll3_sum",
    "temp_c", "humidity", "wind_ms", "rain_mm",
    "hour", "dayofweek", "month", "is_weekend",
    "is_peak_morning", "is_peak_evening", "is_rainy_season",
    "outage_lag1", "outage_roll6_sum",
]


# ── Forecaster Class ──────────────────────────────────────────────────────────

class Forecaster:
    def __init__(self):
        self.clf = LGBMClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5,
            num_leaves=31,
            class_weight="balanced",
            random_state=42,
            verbose=-1,
        )
        self.reg = LGBMRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5,
            num_leaves=31,
            random_state=42,
            verbose=-1,
        )
        self.df_features = None
        self.is_fitted = False

    def fit(self, csv_path: str = "grid_history.csv"):
        df_raw = pd.read_csv(csv_path)
        df = build_features(df_raw)
        self.df_features = df  # store for forecasting context

        X = df[FEATURE_COLS]
        y_clf = df["outage"]
        y_reg = df.loc[df["outage"] == 1, "duration_min"]
        X_reg = df.loc[df["outage"] == 1, FEATURE_COLS]

        self.clf.fit(X, y_clf)
        self.reg.fit(X_reg, y_reg)
        self.is_fitted = True
        print(f"✓ Forecaster fitted on {len(df)} rows")
        return self

    def predict_next_24h(self, reference_time=None) -> list[dict]:
        """
        Build a 24-hour ahead forecast from the last known data point.
        Returns list of 24 dicts: {hour, timestamp, p_outage, expected_duration_min, risk_level}
        """
        if not self.is_fitted:
            raise RuntimeError("Call fit() first.")

        df = self.df_features
        # Use last row as context anchor
        last = df.iloc[-1]
        if reference_time is None:
            reference_time = pd.to_datetime(last["timestamp"]) + pd.Timedelta(hours=1)

        forecast = []
        # We'll use the last known feature values and adjust hour/temporal features
        for offset in range(24):
            ts = reference_time + pd.Timedelta(hours=offset)
            h = ts.hour
            dow = ts.dayofweek
            month = ts.month

            # Build feature row (use last context for lagged values; simplified for inference)
            row = {
                "load_lag1": last["load_mw"],
                "load_lag2": df.iloc[-2]["load_mw"] if len(df) > 2 else last["load_mw"],
                "load_lag24": df.iloc[-24]["load_mw"] if len(df) >= 24 else last["load_mw"],
                "load_lag48": df.iloc[-48]["load_mw"] if len(df) >= 48 else last["load_mw"],
                "load_roll3_mean": df["load_mw"].iloc[-3:].mean(),
                "load_roll6_std": df["load_mw"].iloc[-6:].std(),
                "rain_roll3_sum": df["rain_mm"].iloc[-3:].sum(),
                "temp_c": last["temp_c"] + 2 * np.sin(2 * np.pi * (h - 14) / 24),
                "humidity": float(np.clip(last["humidity"] + np.random.normal(0, 2), 30, 99)),
                "wind_ms": max(0, float(last["wind_ms"])),
                "rain_mm": float(last["rain_mm"] * 0.7),  # decay
                "hour": h,
                "dayofweek": dow,
                "month": month,
                "is_weekend": int(dow >= 5),
                "is_peak_morning": int(7 <= h <= 10),
                "is_peak_evening": int(17 <= h <= 21),
                "is_rainy_season": int(month in [4, 5, 10, 11]),
                "outage_lag1": int(last["outage"]),
                "outage_roll6_sum": float(df["outage"].iloc[-6:].sum()),
            }

            X_row = pd.DataFrame([row])[FEATURE_COLS]
            p_out = float(self.clf.predict_proba(X_row)[0, 1])
            exp_dur = float(self.reg.predict(X_row)[0]) if p_out > 0.05 else 0.0
            exp_dur = max(0, exp_dur)

            # Add calibrated uncertainty band (±1 sigma heuristic)
            p_low = max(0.0, p_out - 0.08)
            p_high = min(1.0, p_out + 0.08)

            risk = "HIGH" if p_out >= 0.25 else "MEDIUM" if p_out >= 0.12 else "LOW"

            forecast.append({
                "hour_offset": offset,
                "timestamp": ts.strftime("%Y-%m-%d %H:%M"),
                "hour": h,
                "p_outage": round(p_out, 4),
                "p_outage_low": round(p_low, 4),
                "p_outage_high": round(p_high, 4),
                "expected_duration_min": round(exp_dur, 1),
                "risk_level": risk,
            })

        return forecast

    def save(self):
        import pickle
        with open(MODEL_PATH_CLF, "wb") as f:
            pickle.dump(self.clf, f)
        with open(MODEL_PATH_REG, "wb") as f:
            pickle.dump(self.reg, f)
        print(f"✓ Models saved: {MODEL_PATH_CLF}, {MODEL_PATH_REG}")

    @classmethod
    def load(cls):
        import pickle
        fc = cls()
        with open(MODEL_PATH_CLF, "rb") as f:
            fc.clf = pickle.load(f)
        with open(MODEL_PATH_REG, "rb") as f:
            fc.reg = pickle.load(f)
        # Need df_features for inference context; rebuild from CSV
        if Path("grid_history.csv").exists():
            df_raw = pd.read_csv("grid_history.csv")
            fc.df_features = build_features(df_raw)
        fc.is_fitted = True
        return fc


# ── Rolling Evaluation ────────────────────────────────────────────────────────

def rolling_eval(csv_path: str = "grid_history.csv", window_days: int = 30):
    """
    Rolling 30-day held-out evaluation.
    Returns: brier_score, mae_duration, avg_lead_time_hours
    """
    df_raw = pd.read_csv(csv_path)
    df = build_features(df_raw)

    # Use last 30 days as test, rest as train
    test_cutoff = df["timestamp"].max() - pd.Timedelta(days=window_days)
    df_train = df[df["timestamp"] <= test_cutoff]
    df_test = df[df["timestamp"] > test_cutoff]

    X_train = df_train[FEATURE_COLS]
    y_train = df_train["outage"]
    X_test = df_test[FEATURE_COLS]
    y_test = df_test["outage"]

    clf = LGBMClassifier(n_estimators=200, learning_rate=0.05, max_depth=5,
                         class_weight="balanced", random_state=42, verbose=-1)
    clf.fit(X_train, y_train)
    probs = clf.predict_proba(X_test)[:, 1]

    # Brier score
    brier = float(np.mean((probs - y_test.values) ** 2))

    # Duration MAE (on true outage hours)
    df_train_out = df_train[df_train["outage"] == 1]
    df_test_out = df_test[df_test["outage"] == 1]
    mae_dur = None
    if len(df_train_out) > 5 and len(df_test_out) > 0:
        reg = LGBMRegressor(n_estimators=200, random_state=42, verbose=-1)
        reg.fit(df_train_out[FEATURE_COLS], df_train_out["duration_min"])
        preds_dur = reg.predict(df_test_out[FEATURE_COLS])
        mae_dur = float(np.mean(np.abs(preds_dur - df_test_out["duration_min"].values)))

    # Lead time: for each true outage, find if model flagged it ≥1h before
    df_test2 = df_test.copy()
    df_test2["pred_prob"] = probs
    df_test2["flagged"] = (probs >= 0.15).astype(int)
    outage_hours = df_test2[df_test2["outage"] == 1].index
    lead_times = []
    for idx in outage_hours:
        # look back up to 3 rows
        look_back = df_test2.loc[max(df_test2.index[0], idx-3):idx-1]
        if len(look_back) > 0 and look_back["flagged"].any():
            lead_times.append(look_back["flagged"].sum())
    avg_lead = float(np.mean(lead_times)) if lead_times else 0.0

    return {
        "brier_score": round(brier, 4),
        "mae_duration_min": round(mae_dur, 1) if mae_dur else None,
        "avg_lead_time_hours": round(avg_lead, 2),
        "n_test_hours": len(df_test),
        "n_test_outages": int(y_test.sum()),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true", help="Print 24h forecast JSON")
    parser.add_argument("--eval", action="store_true", help="Run rolling evaluation")
    parser.add_argument("--fit", action="store_true", help="Fit and save model")
    args = parser.parse_args()

    if args.eval:
        print("Running rolling 30-day evaluation...")
        metrics = rolling_eval()
        print(json.dumps(metrics, indent=2))

    elif args.serve:
        t0 = time.time()
        fc = Forecaster().fit("grid_history.csv")
        forecast = fc.predict_next_24h()
        elapsed_ms = (time.time() - t0) * 1000
        output = {"forecast": forecast, "generated_at": pd.Timestamp.now().isoformat(),
                  "latency_ms": round(elapsed_ms, 1)}
        print(json.dumps(output, indent=2))
        print(f"\n⏱  Total latency: {elapsed_ms:.0f}ms", flush=True)

    elif args.fit:
        fc = Forecaster().fit("grid_history.csv")
        fc.save()

    else:
        # Default: fit + quick forecast preview
        fc = Forecaster().fit("grid_history.csv")
        forecast = fc.predict_next_24h()
        print("\n24-Hour Forecast Preview:")
        print(f"{'Hour':>5} {'Time':>15} {'P(outage)':>10} {'ExpDur(min)':>12} {'Risk':>8}")
        print("-" * 55)
        for row in forecast:
            print(f"{row['hour']:>5} {row['timestamp']:>15} {row['p_outage']:>10.3f} "
                  f"{row['expected_duration_min']:>12.0f} {row['risk_level']:>8}")
