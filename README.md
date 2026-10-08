# VoltPredict — Electricity Bill Prediction

VoltPredict is a Flask + Scikit-learn data science project for estimating an electricity bill from consumption, appliance and environmental inputs.

## Updated features

- Four separate pages: Dashboard, Bill Predictor, Analytics and Saving Tips.
- Sidebar navigation opens each page independently.
- Existing dark VoltPredict UI is retained and expanded.
- Random Forest bill prediction remains the core ML feature.
- Every successful prediction is saved locally in `data/prediction_history.json`.
- Dashboard values update from the latest prediction history.
- Bill Predictor shows the latest result and a live recent-predictions table.
- Analytics includes historical charts plus a personal prediction trend chart.
- Saving Tips are generated from the most recent prediction instead of fixed cards.
- Model status and performance values are loaded dynamically.
- `avg_daily_units` is calculated automatically from units and billing days.

## Run

1. Open PowerShell in the project folder.
2. Activate the virtual environment if you use one:

```powershell
.\venv\Scripts\Activate.ps1
```

3. If needed, install dependencies:

```powershell
pip install -r requirements.txt
```

4. Start the app:

```powershell
python app.py
```

5. Open `http://127.0.0.1:5000/` in the browser.

The supplied `models/bill_model.joblib` is used directly. If the model is missing, run `python train_model.py`.
