# VoltPredict Project Documentation

## Project overview

VoltPredict is a web-based electricity bill prediction application developed as a data science project. It combines a trained Random Forest regression model with a Flask backend and a Chart.js dashboard.

## Main modules

### 1. Dashboard
The Dashboard is the landing page. It displays historical averages, the latest prediction, prediction-run count, model performance and a recent prediction list. These values are loaded through API calls rather than being hard-coded.

### 2. Bill Predictor
The Bill Predictor accepts electricity consumption, previous consumption, billing days, household size, environmental values and appliance usage. Average daily units are calculated automatically. After a successful prediction, the result is saved with a timestamp in `data/prediction_history.json`.

### 3. Analytics
Analytics contains historical monthly trends, appliance usage, unit-consumption distribution and a personal prediction trend. The personal chart changes whenever a new prediction is submitted.

### 4. Saving Tips
Saving Tips are generated from the latest saved prediction. For example, higher AC usage, higher water-heater runtime, a usage spike or hotter temperatures can produce different recommendations.

## Machine-learning workflow

1. Load the electricity dataset.
2. Select the 12 model features.
3. Split the data into training and testing sets.
4. Impute missing values with the median.
5. Train a Random Forest Regressor.
6. Evaluate using MAE, RMSE and R².
7. Save the model to `models/bill_model.joblib`.
8. Save evaluation information to `models/model_metrics.json`.
9. Flask loads the model and exposes prediction and analytics APIs.

## Dynamic data flow

`Bill Predictor form → /api/predict → Random Forest → prediction result → prediction_history.json → Dashboard / Analytics / Saving Tips`

This makes the application change according to the user's latest predictions instead of showing the same static values on every page.

## Run instructions

```powershell
.\venv\Scripts\Activate.ps1
python app.py
```

Then open:

`http://127.0.0.1:5000/`

Available pages:

- `/` — Dashboard
- `/predictor` — Bill Predictor
- `/analytics` — Analytics
- `/tips` — Saving Tips
