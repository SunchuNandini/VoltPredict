
import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
n = 1200
months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

month = rng.choice(months, n)
days = rng.integers(28, 32, n)
occupants = rng.integers(1, 7, n)
temperature = np.clip(rng.normal(30, 4.5, n), 20, 43)
humidity = np.clip(rng.normal(62, 12, n), 25, 95)
ac = np.clip(rng.gamma(2.0, 3.2, n) + np.maximum(temperature-30,0)*0.7, 0, 18)
fan = np.clip(rng.normal(8, 2.2, n), 2, 15)
fridge = np.clip(rng.normal(18, 2, n), 12, 24)
washing = np.clip(rng.normal(10, 4, n), 1, 25)
heater = np.clip(rng.gamma(1.8, 2.0, n), 0, 10)

units = (
    occupants*42 + ac*18 + fan*3.0 + fridge*2.0 +
    washing*1.8 + heater*10 + rng.normal(0, 25, n)
)
units = np.clip(units, 35, 1000)
avg_daily = units / days
previous = np.clip(units * rng.normal(0.96, 0.13, n), 25, 1000)

# Synthetic Indian-style bill with slabs, fixed charge and tax.
def slab_bill(u):
    energy = (
        min(u, 100)*2.0 +
        max(min(u-100, 100), 0)*3.0 +
        max(min(u-200, 200), 0)*4.2 +
        max(min(u-400, 400), 0)*6.0 +
        max(u-800, 0)*8.0
    )
    return 60 + energy + 0.05*energy

energy = np.array([slab_bill(u) for u in units])
bill = energy + 0.8*ac*days + rng.normal(0, 35, n)
bill = np.clip(bill, 80, None)

df = pd.DataFrame({
    "month": month, "days_in_bill": days, "occupants": occupants,
    "temperature_avg": temperature, "humidity_avg": humidity,
    "ac_usage_hours": ac, "fan_usage_hours": fan,
    "refrigerator_hours": fridge, "washing_machine_cycles": washing,
    "water_heater_hours": heater, "units_consumed": units,
    "avg_daily_units": avg_daily, "previous_units": previous,
    "electricity_bill": bill
})
df.to_csv(Path(__file__).resolve().parent / "data" / "electricity_bill_data.csv", index=False)
print("Generated", len(df), "records.")
