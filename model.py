import os
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

MODEL_PATH = "weather_model.pkl"
CSV_PATH = "weatherHistory.csv"

def train_model():
    if not os.path.exists(CSV_PATH):
        print(f"[model.py] '{CSV_PATH}' not found. Download it from:")
        print("  https://www.kaggle.com/datasets/budincsevity/szeged-weather")
        print("  Place it in the project root and run: python model.py")
        return None
    data = pd.read_csv(CSV_PATH, sep=None, engine="python").dropna()
    X = data[["Temperature (C)", "Humidity", "Wind Speed (km/h)", "Pressure (millibars)"]]
    y = data["Summary"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    m = RandomForestClassifier(n_estimators=100, random_state=42)
    m.fit(X_train, y_train)
    joblib.dump(m, MODEL_PATH)
    print(f"[model.py] Model trained and saved to '{MODEL_PATH}'")
    return m

if os.path.exists(MODEL_PATH):
    model = joblib.load(MODEL_PATH)
else:
    model = train_model()

def predict_weather(temp, humidity, wind, pressure):
    if model is None:
        return "Model not available"
    return model.predict([[temp, humidity, wind, pressure]])[0]