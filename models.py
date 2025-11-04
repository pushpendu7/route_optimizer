# models.py
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import joblib
import os

def generate_sample_training_data(n=200):
    """
    Create modest synthetic dataset mapping distance (km), congestion_level, weather_factor -> travel_time_minutes
    """
    rng = np.random.RandomState(42)
    distance_km = rng.uniform(1, 40, size=n)
    congestion = rng.uniform(0.0, 1.0, size=n)
    precip = rng.choice([0, 0.5, 1.0], size=n, p=[0.6, 0.25, 0.15])
    # base speed 40 kmph; speed reduced by congestion and precipitation
    speed = 40 * (1 - 0.5*congestion) * (1 - 0.3*precip)
    travel_time_hours = distance_km / np.clip(speed, 5, None)
    travel_time_minutes = travel_time_hours * 60
    df = pd.DataFrame({
        "distance_km": distance_km,
        "congestion": congestion,
        "precip": precip,
        "travel_time_min": travel_time_minutes
    })
    return df

def train_and_save_model(path="travel_time_model.pkl"):
    df = generate_sample_training_data(500)
    X = df[["distance_km", "congestion", "precip"]]
    y = df["travel_time_min"]
    m = RandomForestRegressor(n_estimators=100, random_state=42)
    m.fit(X, y)
    joblib.dump(m, path)
    print(f"Saved model to {path}")
    return path

def load_model(path="travel_time_model.pkl"):
    if os.path.exists(path):
        return joblib.load(path)
    else:
        raise FileNotFoundError("Model not trained yet. Run train_and_save_model() first.")
