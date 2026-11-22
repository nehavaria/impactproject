# 🌐 NEBULA AI Weather

An AI-powered weather intelligence web app built with Flask.

## ✨ Features
- 🌤 Real-time weather for any city worldwide
- 🤖 AI weather analysis & predictions
- 📊 AQI (Air Quality Index)
- 🏥 Health risk engine
- 📸 Photography location finder with best spots
- 🌾 Smart farming intelligence
- ⚡ Energy consumption optimizer
- 🍽 Food recommendations by weather
- 🐾 Pet safety advisor
- 🌱 Plant care AI
- 💬 NEBULA AI chatbot assistant
- 👤 User profile with search history & favorites
- 🔒 Secure login/register with hashed passwords

## 🚀 Setup

```bash
# 1. Clone the repo
git clone https://github.com/nehavaria/impactproject.git
cd impactproject

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt
```

## 🧠 ML Model Setup (Required)

The trained model file is not included in the repo (too large for GitHub).
You need to download the dataset and train it once:

**Step 1** — Download the dataset from Kaggle:
👉 https://www.kaggle.com/datasets/budincsevity/szeged-weather

**Step 2** — Place `weatherHistory.csv` in the project root folder

**Step 3** — Train the model:
```bash
python model.py
```
This generates `weather_model.pkl` automatically.

## ▶️ Run the App

```bash
python app.py
```

Visit `http://127.0.0.1:5000` in your browser.

## 🛠 Tech Stack
- **Backend:** Python, Flask, SQLite
- **Frontend:** HTML, CSS, JavaScript
- **ML Model:** scikit-learn (Random Forest)
- **APIs:** wttr.in (weather), Open-Meteo (AQI), OpenStreetMap (photo spots)

## 📁 Project Structure
```
impactproject/
├── app.py                # Main Flask application
├── model.py              # ML weather prediction model
├── templates/            # HTML templates
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   └── profile.html
├── static/               # CSS, JS, assets
│   ├── style.css
│   ├── script.js
│   └── bg.mp4
├── requirements.txt      # Python dependencies
└── weatherHistory.csv    # ⚠️ Not included — download from Kaggle
```

## ⚠️ Notes
- `weather_model.pkl` and `weatherHistory.csv` are excluded from git (file size)
- `users.db` is excluded (contains user data)
- Run `python model.py` once after cloning to generate the model
