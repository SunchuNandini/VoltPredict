from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request

BASE = Path(__file__).resolve().parent
MODEL_PATH = BASE / "models" / "bill_model.joblib"
DATA_PATH = BASE / "data" / "electricity_bill_data.csv"
METRICS_PATH = BASE / "models" / "model_metrics.json"
PREDICTIONS_PATH = BASE / "data" / "prediction_history.json"

app = Flask(__name__)

FEATURES = [
    "units_consumed", "avg_daily_units", "days_in_bill",
    "previous_units", "temperature_avg", "humidity_avg",
    "ac_usage_hours", "fan_usage_hours", "refrigerator_hours",
    "washing_machine_cycles", "water_heater_hours", "occupants"
]

RANGES = {
    "units_consumed": (1, 5000),
    "previous_units": (0, 5000),
    "days_in_bill": (1, 31),
    "occupants": (1, 20),
    "temperature_avg": (0, 55),
    "humidity_avg": (0, 100),
    "ac_usage_hours": (0, 24),
    "fan_usage_hours": (0, 24),
    "refrigerator_hours": (0, 24),
    "washing_machine_cycles": (0, 100),
    "water_heater_hours": (0, 24),
}

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

try:
    model = joblib.load(MODEL_PATH)
    MODEL_LOAD_ERROR = None
except Exception as exc:
    model = None
    MODEL_LOAD_ERROR = str(exc)


def get_data() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


def read_metrics() -> dict:
    if METRICS_PATH.exists():
        try:
            return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def read_predictions() -> list[dict]:
    if not PREDICTIONS_PATH.exists():
        return []
    try:
        data = json.loads(PREDICTIONS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_predictions(items: list[dict]) -> None:
    PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Keep the file small while retaining enough recent history for meaningful trends.
    PREDICTIONS_PATH.write_text(json.dumps(items[-100:], indent=2), encoding="utf-8")


def number(payload: dict, name: str) -> float:
    value = payload.get(name)
    if value is None or value == "":
        raise ValueError(f"{name.replace('_', ' ').title()} is required.")
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name.replace('_', ' ').title()} must be a number.")
    lo, hi = RANGES.get(name, (-np.inf, np.inf))
    if not np.isfinite(value) or value < lo or value > hi:
        raise ValueError(f"{name.replace('_', ' ').title()} must be between {lo:g} and {hi:g}.")
    return value


def build_features(payload: dict):
    values = {name: number(payload, name) for name in RANGES}
    values["avg_daily_units"] = values["units_consumed"] / values["days_in_bill"]
    row = pd.DataFrame([[values[f] for f in FEATURES]], columns=FEATURES)
    return row, values


def predict_bill(payload: dict) -> dict:
    if model is None:
        raise RuntimeError("ML model is not loaded. Run train_model.py first.")

    x, values = build_features(payload)
    prediction = max(0.0, float(model.predict(x)[0]))
    units = values["units_consumed"]
    previous = values["previous_units"]
    change_units = units - previous
    change_percent = (change_units / previous * 100) if previous else None

    return {
        "predicted_bill": round(prediction, 2),
        "units": round(units, 2),
        "previous_units": round(previous, 2),
        "avg_daily_units": round(values["avg_daily_units"], 2),
        "change_units": round(change_units, 2),
        "change_percent": round(change_percent, 2) if change_percent is not None else None,
        "estimated_daily_cost": round(prediction / values["days_in_bill"], 2),
        "model": "Random Forest Regression",
    }


def metrics_for_model() -> dict:
    metrics = read_metrics()
    if metrics.get("mae") is not None:
        return metrics

    # Fallback for project ZIPs that contain the trained model but not its metrics file.
    try:
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        from sklearn.model_selection import train_test_split

        df = get_data()
        X, y = df[FEATURES], df["electricity_bill"]
        _, X_test, _, y_test = train_test_split(X, y, test_size=0.20, random_state=42)
        pred = model.predict(X_test)
        metrics = {
            "mae": round(float(mean_absolute_error(y_test, pred)), 2),
            "rmse": round(float(np.sqrt(mean_squared_error(y_test, pred))), 2),
            "r2": round(float(r2_score(y_test, pred)), 4),
            "train_records": int(len(X) - len(X_test)),
            "test_records": int(len(X_test)),
        }
        METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        return metrics
    except Exception:
        return {}


def recent_summary(items: list[dict]) -> dict:
    if not items:
        return {
            "count": 0,
            "latest_bill": None,
            "latest_units": None,
            "average_recent_bill": None,
            "trend_percent": None,
        }

    bills = [float(x["predicted_bill"]) for x in items]
    latest = items[-1]
    trend = None
    if len(items) >= 2 and float(items[-2]["predicted_bill"]):
        trend = (float(latest["predicted_bill"]) - float(items[-2]["predicted_bill"])) / float(items[-2]["predicted_bill"]) * 100
    return {
        "count": len(items),
        "latest_bill": round(float(latest["predicted_bill"]), 2),
        "latest_units": round(float(latest["units"]), 2),
        "average_recent_bill": round(float(np.mean(bills)), 2),
        "trend_percent": round(trend, 2) if trend is not None else None,
    }


def build_tips(record: dict | None) -> list[dict]:
    if not record:
        return [
            {"title": "Cooling", "icon": "❄", "text": "Make your first prediction to receive recommendations based on your actual usage pattern."},
            {"title": "Standby power", "icon": "⚡", "text": "Switch off appliances completely when they are not needed."},
            {"title": "Monitor", "icon": "📊", "text": "Compare every new prediction with your previous cycle to spot unusual increases."},
        ]

    tips = []
    if record["ac_usage_hours"] > 6:
        tips.append({"title": "AC usage", "icon": "❄", "text": f"Your latest AC usage is {record['ac_usage_hours']:.1f} hours/day. Reducing unnecessary runtime can help lower the next bill."})
    if record["water_heater_hours"] > 2.5:
        tips.append({"title": "Water heater", "icon": "♨", "text": f"The latest entry uses the water heater for {record['water_heater_hours']:.1f} hours/day. Shorter heating periods can reduce consumption."})
    if record["washing_machine_cycles"] > 15:
        tips.append({"title": "Washing cycles", "icon": "◌", "text": f"You entered {record['washing_machine_cycles']:.0f} cycles/month. Combining loads where practical may reduce appliance runtime."})
    if record["change_percent"] is not None and record["change_percent"] > 15:
        tips.append({"title": "Usage spike", "icon": "↗", "text": f"Current usage is {record['change_percent']:.1f}% above the previous cycle. Check high-use appliances before the next bill."})
    if record["temperature_avg"] >= 32:
        tips.append({"title": "Hot weather", "icon": "☀", "text": f"The latest temperature input is {record['temperature_avg']:.1f}°C. Cooling demand can rise during hotter periods."})
    if not tips:
        tips.append({"title": "Balanced usage", "icon": "✓", "text": "The latest prediction does not show a major usage spike. Keep monitoring kWh from one billing cycle to the next."})
    tips.append({"title": "Track the trend", "icon": "📈", "text": f"Your latest estimated bill is ₹{record['predicted_bill']:,.0f}. Create another prediction next cycle to build a personal trend."})
    return tips[:4]


@app.route("/")
def index():
    return render_template("dashboard.html", page="dashboard")


@app.route("/predictor")
def predictor_page():
    return render_template("predictor.html", page="predictor")


@app.route("/analytics")
def analytics_page():
    return render_template("analytics.html", page="analytics")


@app.route("/tips")
def tips_page():
    return render_template("tips.html", page="tips")


@app.route("/api/health")
def health():
    return jsonify({
        "status": "online" if model is not None else "error",
        "model_loaded": model is not None,
        "model": "Random Forest Regression",
        "error": MODEL_LOAD_ERROR,
    })


@app.route("/api/predict", methods=["POST"])
def api_predict():
    try:
        payload = request.get_json(silent=True) or {}
        result = predict_bill(payload)

        record = {
            **result,
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "temperature_avg": float(payload.get("temperature_avg", 0)),
            "humidity_avg": float(payload.get("humidity_avg", 0)),
            "ac_usage_hours": float(payload.get("ac_usage_hours", 0)),
            "fan_usage_hours": float(payload.get("fan_usage_hours", 0)),
            "refrigerator_hours": float(payload.get("refrigerator_hours", 0)),
            "washing_machine_cycles": float(payload.get("washing_machine_cycles", 0)),
            "water_heater_hours": float(payload.get("water_heater_hours", 0)),
            "occupants": float(payload.get("occupants", 0)),
            "days_in_bill": float(payload.get("days_in_bill", 0)),
        }
        items = read_predictions()
        items.append(record)
        save_predictions(items)
        result["timestamp"] = record["timestamp"]
        result["recent_count"] = len(items)
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/summary")
def summary():
    df = get_data()
    items = read_predictions()
    rs = recent_summary(items)
    metrics = metrics_for_model()
    return jsonify({
        "records": int(len(df)),
        "avg_units": round(float(df["units_consumed"].mean()), 2),
        "avg_bill": round(float(df["electricity_bill"].mean()), 2),
        "max_bill": round(float(df["electricity_bill"].max()), 2),
        "min_bill": round(float(df["electricity_bill"].min()), 2),
        "median_bill": round(float(df["electricity_bill"].median()), 2),
        "mae": metrics.get("mae"),
        "rmse": metrics.get("rmse"),
        "r2": metrics.get("r2"),
        "recent": rs,
    })


@app.route("/api/history")
def history():
    df = get_data()
    monthly = df.groupby("month", sort=False).agg(
        units=("units_consumed", "mean"),
        bill=("electricity_bill", "mean"),
    ).reset_index()
    monthly["order"] = monthly["month"].map({m: i for i, m in enumerate(MONTH_ORDER)})
    monthly = monthly.sort_values("order")
    return jsonify(monthly[["month", "units", "bill"]].round(2).to_dict(orient="records"))


@app.route("/api/recent")
def recent():
    items = read_predictions()
    return jsonify({"predictions": items[-20:][::-1], "summary": recent_summary(items)})


@app.route("/api/analytics")
def analytics():
    df = get_data()
    items = read_predictions()

    appliance = [
        {"name": "AC", "value": round(float(df["ac_usage_hours"].mean()), 2), "unit": "hrs/day"},
        {"name": "Fan", "value": round(float(df["fan_usage_hours"].mean()), 2), "unit": "hrs/day"},
        {"name": "Refrigerator", "value": round(float(df["refrigerator_hours"].mean()), 2), "unit": "hrs/day"},
        {"name": "Washing machine", "value": round(float(df["washing_machine_cycles"].mean()), 2), "unit": "cycles/month"},
        {"name": "Water heater", "value": round(float(df["water_heater_hours"].mean()), 2), "unit": "hrs/day"},
    ]

    bins = [-1, 100, 200, 400, 800, np.inf]
    labels = ["≤100", "101–200", "201–400", "401–800", "800+"]
    distribution = pd.cut(df["units_consumed"], bins=bins, labels=labels).value_counts(sort=False).reset_index()
    distribution.columns = ["range", "records"]
    distribution["records"] = distribution["records"].astype(int)

    recent_series = [
        {"label": x["timestamp"], "bill": x["predicted_bill"], "units": x["units"]}
        for x in items[-20:]
    ]

    latest = items[-1] if items else None
    return jsonify({
        "appliances": appliance,
        "distribution": distribution.to_dict(orient="records"),
        "recent_predictions": recent_series,
        "latest": latest,
    })


@app.route("/api/tips", methods=["GET", "POST"])
def tips_api():
    items = read_predictions()
    latest = items[-1] if items else None
    return jsonify({"tips": build_tips(latest), "latest": latest, "prediction_count": len(items)})


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
