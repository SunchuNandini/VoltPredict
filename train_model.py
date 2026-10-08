import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

BASE = Path(__file__).resolve().parent
DATA = BASE / "data" / "electricity_bill_data.csv"
MODEL = BASE / "models" / "bill_model.joblib"
METRICS = BASE / "models" / "model_metrics.json"

FEATURES = [
    "units_consumed", "avg_daily_units", "days_in_bill",
    "previous_units", "temperature_avg", "humidity_avg",
    "ac_usage_hours", "fan_usage_hours", "refrigerator_hours",
    "washing_machine_cycles", "water_heater_hours", "occupants"
]
TARGET = "electricity_bill"

df = pd.read_csv(DATA)
X, y = df[FEATURES], df[TARGET]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42)

model = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("regressor", RandomForestRegressor(
        n_estimators=450,
        max_depth=16,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )),
])
model.fit(X_train, y_train)
pred = model.predict(X_test)

mae = float(mean_absolute_error(y_test, pred))
rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
r2 = float(r2_score(y_test, pred))

rf = model.named_steps["regressor"]
importance = dict(sorted(zip(FEATURES, rf.feature_importances_), key=lambda x: x[1], reverse=True))
metrics = {
    "mae": round(mae, 2),
    "rmse": round(rmse, 2),
    "r2": round(r2, 4),
    "train_records": int(len(X_train)),
    "test_records": int(len(X_test)),
    "features": FEATURES,
    "feature_importance": {k: round(float(v), 6) for k, v in importance.items()},
}

MODEL.parent.mkdir(parents=True, exist_ok=True)
joblib.dump(model, MODEL)
METRICS.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

print("Training electricity bill prediction model...")
print("\n==============================")
print("MODEL PERFORMANCE")
print("==============================")
print(f"MAE  : ₹{mae:.2f}")
print(f"RMSE : ₹{rmse:.2f}")
print(f"R²   : {r2:.4f}")
print("==============================")
print(f"\nModel saved successfully:\n{MODEL}")
print(f"Metrics saved successfully:\n{METRICS}")
