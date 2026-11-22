from flask import Flask, render_template, request, redirect, session, flash, jsonify
from model import predict_weather
import requests
import sqlite3
import hashlib
import json
from datetime import datetime, timedelta

app = Flask(__name__)
import os
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production")

def get_db():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

with get_db() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS search_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            city TEXT,
            searched_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_favorites(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            city TEXT,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(username, city)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS weather_cache(
            city TEXT PRIMARY KEY,
            data TEXT,
            cached_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def get_cached_weather(city):
    with get_db() as conn:
        row = conn.execute(
            "SELECT data, cached_at FROM weather_cache WHERE city=?", (city.lower(),)
        ).fetchone()
    if row:
        cached_time = datetime.strptime(row["cached_at"], "%Y-%m-%d %H:%M:%S")
        if datetime.utcnow() - cached_time < timedelta(minutes=30):
            return json.loads(row["data"])
    return None

def set_cached_weather(city, data):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO weather_cache(city, data, cached_at) VALUES(?, ?, datetime('now'))",
            (city.lower(), json.dumps(data))
        )
        conn.commit()

def get_ai_analysis(temp, humidity, wind, description):
    desc = description.lower()
    lines = []

    if temp >= 38:
        lines.append("🔥 Extreme heat detected. Risk of heatstroke — stay indoors.")
    elif temp >= 32:
        lines.append("🌡️ High temperature detected. Stay hydrated and avoid direct sun.")
    elif temp <= 0:
        lines.append("🧊 Freezing conditions. Risk of ice on roads and surfaces.")
    elif temp <= 10:
        lines.append("🥶 Cold weather detected. Layer up before heading out.")
    else:
        lines.append("🌤️ Temperature is comfortable for outdoor activities.")

    if humidity >= 85:
        lines.append("💧 Very high humidity. Possible rain or drizzle in the next few hours.")
    elif humidity >= 70:
        lines.append("💧 Elevated humidity detected. Carry an umbrella as a precaution.")
    else:
        lines.append("✅ Humidity levels are normal.")

    if wind >= 60:
        lines.append("🌪️ Strong winds detected. Avoid open areas and secure loose objects.")
    elif wind >= 30:
        lines.append("💨 Moderate winds. Be cautious while driving or cycling.")
    else:
        lines.append("🍃 Wind conditions are calm.")

    if "rain" in desc or "drizzle" in desc:
        lines.append("🌧️ Precipitation active. Roads may be slippery — drive carefully.")
    if "thunder" in desc or "storm" in desc:
        lines.append("⛈️ Thunderstorm conditions. Stay indoors and unplug electronics.")
    if "snow" in desc or "blizzard" in desc:
        lines.append("❄️ Snowfall detected. Travel disruptions likely.")
    if "fog" in desc or "mist" in desc:
        lines.append("🌫️ Low visibility due to fog. Use fog lights while driving.")

    return lines


def get_outfit(temp, description):
    desc = description.lower()
    if "rain" in desc or "drizzle" in desc or "shower" in desc:
        return {"icon": "🌂", "title": "Rain Gear", "tip": "Wear a waterproof jacket and carry an umbrella. Avoid light fabrics."}
    if "snow" in desc or "blizzard" in desc:
        return {"icon": "🧥", "title": "Winter Outfit", "tip": "Heavy coat, thermal layers, gloves, and waterproof boots recommended."}
    if "thunder" in desc or "storm" in desc:
        return {"icon": "⛈️", "title": "Stay Indoors", "tip": "Best to stay inside. If going out, wear a raincoat and avoid metal objects."}
    if temp >= 35:
        return {"icon": "👕", "title": "Light & Breathable", "tip": "Wear loose cotton or linen clothes. Light colors reflect heat better."}
    if temp >= 25:
        return {"icon": "👗", "title": "Casual Wear", "tip": "T-shirt and shorts or light trousers. Sunglasses and sunscreen recommended."}
    if temp >= 15:
        return {"icon": "🧣", "title": "Light Layers", "tip": "A light jacket or hoodie over a t-shirt. Comfortable jeans work well."}
    if temp >= 5:
        return {"icon": "🧤", "title": "Warm Outfit", "tip": "Wear a warm jacket, scarf, and gloves. Layering is key."}
    return {"icon": "🧥", "title": "Heavy Winter Gear", "tip": "Full winter coat, thermal underlayers, hat, gloves, and insulated boots."}


def get_mood(temp, description):
    desc = description.lower()
    if "rain" in desc or "drizzle" in desc:
        return {"emoji": "☕", "message": "Perfect weather to curl up with a hot coffee and a good book."}
    if "snow" in desc:
        return {"emoji": "⛄", "message": "Magical snow day! Great time for hot chocolate and cozy vibes."}
    if "thunder" in desc or "storm" in desc:
        return {"emoji": "🎬", "message": "Storm outside — perfect excuse for a movie marathon indoors."}
    if "sunny" in desc or "clear" in desc:
        if temp >= 28:
            return {"emoji": "🏖️", "message": "Gorgeous sunny day! Great for a beach trip or outdoor picnic."}
        return {"emoji": "🌞", "message": "Beautiful clear skies! Perfect for a walk or outdoor workout."}
    if "cloud" in desc or "overcast" in desc:
        return {"emoji": "🎵", "message": "Moody cloudy skies — ideal for music, art, or a creative session."}
    if temp <= 5:
        return {"emoji": "🔥", "message": "Freezing outside! Stay warm, light a candle, and enjoy the chill indoors."}
    return {"emoji": "😊", "message": "Nice weather overall. A great day to get things done!"}


def get_alerts(temp, wind, description, humidity):
    desc = description.lower()
    alerts = []
    if temp >= 42:
        alerts.append({"level": "critical", "icon": "🚨", "title": "Extreme Heatwave Warning", "msg": "Dangerous heat levels. Avoid all outdoor activity. Risk of heat exhaustion."})
    elif temp >= 38:
        alerts.append({"level": "warning", "icon": "⚠️", "title": "Heatwave Alert", "msg": "Very high temperatures. Stay hydrated and seek shade."})
    if temp <= -5:
        alerts.append({"level": "critical", "icon": "🚨", "title": "Severe Freeze Warning", "msg": "Extreme cold. Risk of frostbite within minutes of exposure."})
    if wind >= 80:
        alerts.append({"level": "critical", "icon": "🌪️", "title": "Severe Storm Warning", "msg": "Dangerous wind speeds. Do not go outside. Secure all loose objects."})
    elif wind >= 50:
        alerts.append({"level": "warning", "icon": "💨", "title": "High Wind Advisory", "msg": "Strong winds may cause travel disruptions and falling debris."})
    if "thunder" in desc or "storm" in desc:
        alerts.append({"level": "warning", "icon": "⛈️", "title": "Thunderstorm Alert", "msg": "Lightning risk is high. Stay indoors and away from windows."})
    if "blizzard" in desc or ("snow" in desc and wind >= 40):
        alerts.append({"level": "critical", "icon": "❄️", "title": "Blizzard Warning", "msg": "Whiteout conditions possible. Avoid all travel."})
    if humidity >= 90 and temp >= 30:
        alerts.append({"level": "warning", "icon": "💧", "title": "Flood Risk Advisory", "msg": "Extreme humidity with heat may indicate heavy rainfall and flooding risk."})
    return alerts


def get_aqi(lat, lon):
    try:
        url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=us_aqi,pm2_5,pm10"
        r = requests.get(url, timeout=5)
        data = r.json()
        aqi = int(data["current"]["us_aqi"])
        pm25 = round(data["current"]["pm2_5"], 1)
        if aqi <= 50:
            level, color, advice = "Good", "#22c55e", "Air quality is satisfactory. Enjoy outdoor activities."
        elif aqi <= 100:
            level, color, advice = "Moderate", "#eab308", "Acceptable air quality. Unusually sensitive people should limit prolonged outdoor exertion."
        elif aqi <= 150:
            level, color, advice = "Unhealthy for Sensitive Groups", "#f97316", "Sensitive groups should reduce outdoor activity. Consider wearing a mask."
        elif aqi <= 200:
            level, color, advice = "Unhealthy", "#ef4444", "Everyone may experience health effects. Wear a mask outdoors."
        elif aqi <= 300:
            level, color, advice = "Very Unhealthy", "#a855f7", "Health alert! Avoid outdoor activities. N95 mask strongly recommended."
        else:
            level, color, advice = "Hazardous", "#7f1d1d", "Emergency conditions. Stay indoors with windows closed."
        return {"aqi": aqi, "pm25": pm25, "level": level, "color": color, "advice": advice}
    except Exception:
        return None


def get_health_risks(temp, humidity, uv_index, wind, description, aqi_level=None):
    desc = description.lower()
    risks = []

    # UV / Skin
    if uv_index >= 11:
        risks.append({"icon": "🔴", "risk": "Extreme UV Radiation", "detail": "Skin damage in under 10 min. Use SPF 50+, wear full-sleeve clothing and a hat.", "level": "critical"})
    elif uv_index >= 8:
        risks.append({"icon": "🟠", "risk": "Very High UV — Skin Danger", "detail": "High risk of sunburn. Apply SPF 30+ every 2 hours. Avoid sun 10am–4pm.", "level": "high"})
    elif uv_index >= 6:
        risks.append({"icon": "🟡", "risk": "Moderate UV Exposure", "detail": "Wear sunscreen SPF 15+. Sunglasses recommended.", "level": "medium"})

    # Heatstroke
    if temp >= 40:
        risks.append({"icon": "🔥", "risk": "Heatstroke Probability: HIGH", "detail": "Dangerous heat. Stay indoors, drink 3–4L water, avoid physical exertion.", "level": "critical"})
    elif temp >= 35 and humidity >= 60:
        risks.append({"icon": "🌡️", "risk": "Heat Exhaustion Risk", "detail": "High heat + humidity combo. Take breaks in shade, stay hydrated.", "level": "high"})

    # Dehydration
    if temp >= 35:
        risks.append({"icon": "💧", "risk": "Dehydration Risk: Elevated", "detail": "Drink at least 500ml water per hour during outdoor activity.", "level": "high"})
    elif temp >= 28:
        risks.append({"icon": "💧", "risk": "Dehydration Risk: Moderate", "detail": "Drink 2–3L of water today. Avoid sugary drinks.", "level": "medium"})

    # Asthma / Respiratory
    if aqi_level in ["Unhealthy", "Very Unhealthy", "Hazardous"]:
        risks.append({"icon": "😷", "risk": "Asthma & Respiratory Danger", "detail": "Poor air quality detected. Asthma patients must carry inhalers. Wear N95 mask.", "level": "critical"})
    elif aqi_level == "Unhealthy for Sensitive Groups":
        risks.append({"icon": "😷", "risk": "Respiratory Caution", "detail": "Sensitive individuals should limit outdoor exposure. Keep windows closed.", "level": "medium"})

    # Migraine
    if ("thunder" in desc or "storm" in desc) or (humidity >= 80 and temp >= 28):
        risks.append({"icon": "🧠", "risk": "Migraine Trigger Risk", "detail": "Pressure changes and high humidity are known migraine triggers. Stay hydrated and rest.", "level": "medium"})

    # Cold / Flu
    if temp <= 5:
        risks.append({"icon": "🤧", "risk": "Cold & Flu Risk: High", "detail": "Cold exposure weakens immunity. Wear warm layers and avoid wet conditions.", "level": "high"})

    if not risks:
        risks.append({"icon": "✅", "risk": "No Significant Health Risks", "detail": "Current weather conditions pose no major health threats. Stay active and enjoy the day!", "level": "safe"})

    return risks


def get_farming_intel(temp, humidity, wind, description):
    desc = description.lower()
    tips = []

    if "rain" in desc or "drizzle" in desc:
        tips.append({"icon": "🌧️", "tip": "Natural irrigation active. Skip watering today — save water resources."})
        tips.append({"icon": "⚠️", "tip": "Avoid pesticide application during rain — chemicals will wash away."})
    elif humidity >= 80:
        tips.append({"icon": "💧", "tip": "High humidity detected. Risk of fungal diseases on crops. Ensure proper drainage."})
    elif humidity <= 30:
        tips.append({"icon": "🚿", "tip": "Low humidity — increase irrigation frequency. Crops may dry out quickly."})
    else:
        tips.append({"icon": "✅", "tip": "Humidity levels are ideal for most crops. Normal irrigation schedule recommended."})

    if temp >= 38:
        tips.append({"icon": "🔥", "tip": "Extreme heat — water crops in early morning or evening to reduce evaporation."})
        tips.append({"icon": "🌿", "tip": "Heat-sensitive crops (lettuce, spinach) may bolt. Consider shade netting."})
    elif temp >= 28:
        tips.append({"icon": "☀️", "tip": "Good temperature for warm-season crops: tomatoes, peppers, corn, and beans."})
    elif temp <= 10:
        tips.append({"icon": "❄️", "tip": "Cold conditions — protect frost-sensitive crops with covers or mulch."})
    else:
        tips.append({"icon": "🌱", "tip": "Ideal growing conditions. Good time for transplanting seedlings."})

    if wind >= 40:
        tips.append({"icon": "💨", "tip": "Strong winds — stake tall plants and secure greenhouse covers."})

    if "sunny" in desc or "clear" in desc:
        tips.append({"icon": "🌻", "tip": "Clear skies — excellent day for harvesting and field work."})

    return tips


def get_energy_tips(temp, description, uv_index):
    desc = description.lower()
    tips = []
    solar_eff = 0

    if "sunny" in desc or "clear" in desc:
        solar_eff = 90 if uv_index >= 7 else 75
        tips.append({"icon": "☀️", "tip": f"Excellent solar conditions. Solar panels operating at ~{solar_eff}% efficiency today."})
        tips.append({"icon": "💡", "tip": "Use natural daylight — keep blinds open and delay artificial lighting."})
    elif "cloud" in desc or "overcast" in desc:
        solar_eff = 35
        tips.append({"icon": "⛅", "tip": "Cloudy skies reduce solar efficiency to ~35%. Supplement with grid power."})
    elif "rain" in desc:
        solar_eff = 15
        tips.append({"icon": "🌧️", "tip": "Rain significantly reduces solar output (~15%). Rely on stored or grid energy."})

    if temp >= 35:
        tips.append({"icon": "❄️", "tip": "Set AC to 24–26°C for optimal cooling efficiency. Each degree lower adds ~6% energy cost."})
        tips.append({"icon": "🔌", "tip": "Peak cooling demand — avoid running heavy appliances between 12pm–4pm."})
    elif temp <= 10:
        tips.append({"icon": "🔥", "tip": "Set heater to 20–22°C. Use draft stoppers on doors to retain heat."})
        tips.append({"icon": "🧥", "tip": "Layer up indoors before increasing heating — saves up to 10% energy."})
    else:
        tips.append({"icon": "🌿", "tip": "Mild weather — consider turning off AC/heating and opening windows instead."})

    saving = solar_eff // 5
    if saving > 0:
        tips.append({"icon": "💰", "tip": f"Estimated energy saving today: ~{saving}% if solar panels are active."})

    return tips


def get_productivity(temp, humidity, description):
    desc = description.lower()
    score = 75
    mood_label = "Neutral"
    study_time = "Morning (8–11am)"
    sleep_quality = "Good"
    tips = []

    if "sunny" in desc or "clear" in desc:
        score = 85
        mood_label = "Energetic & Positive"
        tips.append("☀️ Bright weather boosts serotonin. Great day for creative and analytical work.")
        tips.append("📚 Best study window: Morning 8–11am and Evening 6–8pm.")
    elif "rain" in desc or "drizzle" in desc:
        score = 68
        mood_label = "Calm & Reflective"
        tips.append("🌧️ Rain creates a focused indoor atmosphere. Ideal for deep reading or writing.")
        tips.append("📚 Best study window: Afternoon 2–5pm with ambient music.")
        study_time = "Afternoon (2–5pm)"
    elif "cloud" in desc or "overcast" in desc:
        score = 62
        mood_label = "Slightly Low Energy"
        tips.append("☁️ Overcast skies may reduce motivation by 10–15%. Take short breaks every 45 min.")
        tips.append("💡 Use bright indoor lighting to compensate for lack of natural light.")
        study_time = "Morning (9am–12pm)"
    elif "thunder" in desc or "storm" in desc:
        score = 55
        mood_label = "Anxious / Distracted"
        tips.append("⛈️ Storm conditions increase anxiety. Avoid high-stress tasks. Focus on routine work.")
        tips.append("🎵 Calm music or white noise can help maintain concentration.")
        study_time = "Short sessions only"

    if temp >= 35:
        score -= 10
        sleep_quality = "Poor (heat disrupts sleep)"
        tips.append("🌡️ High heat reduces cognitive performance. Keep workspace cool (22–24°C).")
    elif temp <= 5:
        score -= 8
        sleep_quality = "Fair (cold may disturb sleep)"
        tips.append("🥶 Cold weather increases fatigue. Stay warm and take warm drinks to stay alert.")
    else:
        sleep_quality = "Good"

    if humidity >= 80:
        score -= 7
        tips.append("💧 High humidity causes discomfort and reduces focus. Use a dehumidifier if possible.")

    score = max(30, min(100, score))
    return {"score": score, "mood": mood_label, "study_time": study_time, "sleep": sleep_quality, "tips": tips}


def get_food_recommendation(temp, description):
    desc = description.lower()
    if "rain" in desc or "drizzle" in desc or "shower" in desc:
        return {"emoji": "☕", "title": "Rainy Day Comfort Food", "items": [
            {"icon": "☕", "name": "Hot Coffee", "reason": "Warm up with a cozy cup"},
            {"icon": "🍜", "name": "Maggi / Noodles", "reason": "Quick, warm and satisfying"},
            {"icon": "🥣", "name": "Hot Soup", "reason": "Perfect for rainy weather"},
            {"icon": "🫖", "name": "Masala Chai", "reason": "Classic rainy day drink"}
        ]}
    if "snow" in desc or "blizzard" in desc:
        return {"emoji": "🍲", "title": "Winter Warmers", "items": [
            {"icon": "🍲", "name": "Hot Stew", "reason": "Hearty and warming"},
            {"icon": "🍫", "name": "Hot Chocolate", "reason": "Classic snow day drink"},
            {"icon": "🥐", "name": "Baked Goods", "reason": "Warm from the oven"},
            {"icon": "🍵", "name": "Green Tea", "reason": "Keeps you warm and healthy"}
        ]}
    if "thunder" in desc or "storm" in desc:
        return {"emoji": "🍕", "title": "Storm Night Snacks", "items": [
            {"icon": "🍕", "name": "Pizza", "reason": "Perfect indoor meal"},
            {"icon": "🍿", "name": "Popcorn", "reason": "Movie night snack"},
            {"icon": "☕", "name": "Hot Coffee", "reason": "Stay cozy indoors"},
            {"icon": "🍪", "name": "Cookies", "reason": "Sweet comfort food"}
        ]}
    if temp >= 38:
        return {"emoji": "🥤", "title": "Beat the Heat", "items": [
            {"icon": "🥤", "name": "Cold Lemonade", "reason": "Refreshing and hydrating"},
            {"icon": "🍦", "name": "Ice Cream", "reason": "Cool down instantly"},
            {"icon": "🍉", "name": "Watermelon", "reason": "92% water, beats dehydration"},
            {"icon": "🥥", "name": "Coconut Water", "reason": "Natural electrolytes"}
        ]}
    if temp >= 28:
        return {"emoji": "🍹", "title": "Warm Weather Refreshers", "items": [
            {"icon": "🍹", "name": "Fresh Juice", "reason": "Vitamins and hydration"},
            {"icon": "🥗", "name": "Light Salad", "reason": "Easy on digestion in heat"},
            {"icon": "🍧", "name": "Shaved Ice", "reason": "Instant cooling treat"},
            {"icon": "🫐", "name": "Fresh Fruits", "reason": "Hydrating and nutritious"}
        ]}
    if temp <= 10:
        return {"emoji": "🍜", "title": "Cold Weather Comfort", "items": [
            {"icon": "🍜", "name": "Hot Ramen", "reason": "Warming and filling"},
            {"icon": "🫖", "name": "Ginger Tea", "reason": "Boosts immunity in cold"},
            {"icon": "🥘", "name": "Casserole", "reason": "Hearty winter meal"},
            {"icon": "🍞", "name": "Toast & Butter", "reason": "Simple warm comfort"}
        ]}
    return {"emoji": "🍽️", "title": "Good Weather Meals", "items": [
        {"icon": "🥪", "name": "Sandwich", "reason": "Great for outdoor eating"},
        {"icon": "🍱", "name": "Bento Box", "reason": "Perfect picnic food"},
        {"icon": "🥤", "name": "Smoothie", "reason": "Healthy and refreshing"},
        {"icon": "🍎", "name": "Fresh Fruits", "reason": "Light and energizing"}
    ]}


def get_photo_spots(lat, lon, city):
    try:
        headers = {"User-Agent": "NebulAIWeather/1.0"}
        skip_words = ["station", "university", "college", "school", "hospital", "road", "street",
                      "highway", "metro", "railway", "bus", "district", "ward", "municipality",
                      "constituency", "tehsil", "taluk", "block", "it park", "flyover",
                      "income tax", "central excise", "gate rd"]
        seen = set()
        spots = []
        place_types = ["fort", "palace", "temple", "museum", "garden", "waterfall",
                       "monument", "park", "lake", "mosque", "church", "ghat", "cave", "sanctuary"]

        for ptype in place_types:
            if len(spots) >= 6:
                break
            try:
                r = requests.get(
                    f"https://nominatim.openstreetmap.org/search?q={ptype}+{city}&format=json&limit=3&addressdetails=0",
                    headers=headers, timeout=4
                ).json()
                for p in r:
                    name = p.get("display_name", "").split(",")[0].strip()
                    if not name or name.lower() in seen:
                        continue
                    if any(w in name.lower() for w in skip_words):
                        continue
                    if len(name.split()) == 1:
                        continue
                    seen.add(name.lower())
                    spots.append({
                        "name": name,
                        "best_time": "6:00 AM - 7:30 AM  or  5:30 PM - 7:00 PM",
                        "why": f"Famous {ptype} — great for golden hour photography",
                        "how": f"Search '{name}' on Google Maps for directions",
                        "maps_url": f"https://www.google.com/maps?q={p['lat']},{p['lon']}"
                    })
                    if len(spots) >= 6:
                        break
            except Exception:
                continue
        return spots
    except Exception:
        return []


def get_photography_tips(temp, description, uv_index, city=""):
    desc = description.lower()
    city_lower = city.lower().strip()
    tips = []
    score = 0
    golden = "6:00 AM - 7:30 AM  and  5:30 PM - 7:00 PM"

    if "sunny" in desc or "clear" in desc:
        score = 90
        tips.append({"icon": "📸", "tip": "Excellent day for outdoor photography! Clear skies give sharp, vibrant shots."})
        tips.append({"icon": "🌅", "tip": "Golden hour is perfect today. Shoot during sunrise or sunset for warm tones."})
        if uv_index >= 7:
            tips.append({"icon": "⚠️", "tip": f"Midday sun is harsh (UV {uv_index}). Avoid 11am-3pm for portraits — harsh shadows."})
    elif "cloud" in desc or "overcast" in desc:
        score = 75
        tips.append({"icon": "📸", "tip": "Overcast skies act as a natural softbox — ideal for portrait photography!"})
        tips.append({"icon": "🎨", "tip": "Colors appear more saturated under clouds. Great for street and nature shots."})
        tips.append({"icon": "🌥️", "tip": "No harsh shadows today — perfect for even lighting on subjects."})
    elif "rain" in desc or "drizzle" in desc:
        score = 60
        tips.append({"icon": "🌧️", "tip": "Rain creates beautiful reflections on streets and puddles — use them!"})
        tips.append({"icon": "📸", "tip": "Protect your camera with a rain cover. Shoot from sheltered spots."})
        tips.append({"icon": "🌈", "tip": "Watch for rainbows after the rain — golden photography opportunity!"})
    elif "fog" in desc or "mist" in desc:
        score = 85
        tips.append({"icon": "🌫️", "tip": "Fog creates a dramatic, moody atmosphere — perfect for artistic shots!"})
        tips.append({"icon": "📸", "tip": "Use fog to add depth and mystery to landscapes and cityscapes."})
    elif "thunder" in desc or "storm" in desc:
        score = 40
        tips.append({"icon": "⛈️", "tip": "Storm photography is dramatic but risky. Shoot from indoors through windows."})
        tips.append({"icon": "⚡", "tip": "Lightning shots require a tripod and long exposure. Stay safe indoors!"})
    elif "snow" in desc:
        score = 80
        tips.append({"icon": "❄️", "tip": "Snow creates a magical white landscape — perfect for dramatic shots!"})
        tips.append({"icon": "📸", "tip": "Use a fast shutter speed to freeze falling snowflakes."})
    else:
        score = 70
        tips.append({"icon": "📸", "tip": "Decent conditions for photography. Check the light before shooting."})

    # City-specific photography spots
    CITY_SPOTS = {
        "dehradun": [
            {"name": "Robber's Cave (Guchhupani)", "best_time": "6:30 AM - 8:00 AM", "why": "Morning mist over the cave stream creates magical shots", "how": "Take an auto or cab from Clock Tower, 8 km, ~20 min"},
            {"name": "Sahastradhara Waterfall", "best_time": "5:30 PM - 7:00 PM", "why": "Golden hour light on the sulphur springs and waterfall", "how": "Bus from ISBT or cab, 14 km from city center, ~30 min"},
            {"name": "Mindrolling Monastery", "best_time": "7:00 AM - 9:00 AM", "why": "Soft morning light on the white stupa and gardens", "how": "Auto from Paltan Bazaar, 5 km, ~15 min"},
            {"name": "Tapkeshwar Temple", "best_time": "6:00 AM - 7:30 AM", "why": "Sunrise light through the cave temple is stunning", "how": "Auto or cab from Clock Tower, 5.5 km, ~15 min"},
        ],
        "delhi": [
            {"name": "India Gate", "best_time": "6:00 AM - 7:30 AM", "why": "Empty roads and golden sunrise light on the monument", "how": "Metro to Central Secretariat, 5 min walk"},
            {"name": "Humayun's Tomb", "best_time": "5:30 PM - 7:00 PM", "why": "Warm sunset tones on the Mughal architecture", "how": "Metro to JLN Stadium, auto to tomb, ~10 min"},
            {"name": "Lotus Temple", "best_time": "6:00 AM - 8:00 AM", "why": "Reflections in the pools with morning light", "how": "Metro to Kalkaji Mandir, 5 min walk"},
            {"name": "Chandni Chowk", "best_time": "7:00 AM - 9:00 AM", "why": "Street photography before crowds arrive", "how": "Metro to Chandni Chowk station, direct"},
        ],
        "mumbai": [
            {"name": "Marine Drive", "best_time": "6:00 AM - 7:30 AM", "why": "Sunrise over the Arabian Sea with the Queen's Necklace curve", "how": "Taxi or local train to Churchgate, 5 min walk"},
            {"name": "Gateway of India", "best_time": "5:30 PM - 7:00 PM", "why": "Golden hour with boats and the iconic arch", "how": "Taxi to Colaba, 5 min walk from Colaba Causeway"},
            {"name": "Bandra-Worli Sea Link", "best_time": "6:00 AM - 7:00 AM", "why": "Misty morning shots of the cable-stayed bridge", "how": "Taxi from Bandra station, 10 min"},
            {"name": "Dharavi Rooftop", "best_time": "5:30 PM - 6:30 PM", "why": "Aerial cityscape photography at sunset", "how": "Auto from Sion station, 10 min"},
        ],
        "paris": [
            {"name": "Eiffel Tower", "best_time": "6:00 AM - 7:30 AM", "why": "Empty Champ de Mars with golden sunrise behind the tower", "how": "Metro Line 6 to Bir-Hakeim, 5 min walk"},
            {"name": "Montmartre", "best_time": "6:30 AM - 8:00 AM", "why": "Cobblestone streets empty, Sacré-Cœur in soft morning light", "how": "Metro Line 12 to Abbesses, walk up the hill"},
            {"name": "Seine River Banks", "best_time": "5:30 PM - 7:00 PM", "why": "Golden reflections on the river with Notre-Dame", "how": "Walk from any central Metro station"},
        ],
        "london": [
            {"name": "Tower Bridge", "best_time": "6:00 AM - 7:30 AM", "why": "Misty Thames with empty bridge at sunrise", "how": "Tube to Tower Hill, 5 min walk"},
            {"name": "Greenwich Park", "best_time": "5:30 PM - 7:00 PM", "why": "Panoramic London skyline at golden hour", "how": "DLR to Cutty Sark, 10 min walk uphill"},
        ],
        "new york": [
            {"name": "Brooklyn Bridge", "best_time": "6:00 AM - 7:30 AM", "why": "Manhattan skyline behind the bridge at sunrise", "how": "Subway to High Street, walk to bridge entrance"},
            {"name": "Top of the Rock", "best_time": "5:30 PM - 7:00 PM", "why": "360 degree golden hour view of Manhattan", "how": "Subway to 47-50 Sts Rockefeller Center"},
        ],
        "tokyo": [
            {"name": "Senso-ji Temple", "best_time": "6:00 AM - 7:30 AM", "why": "Ancient temple with morning mist before tourists arrive", "how": "Tokyo Metro Ginza Line to Asakusa, 5 min walk"},
            {"name": "Shibuya Crossing", "best_time": "6:30 PM - 8:00 PM", "why": "Neon lights and crowds create iconic long-exposure shots", "how": "JR Yamanote Line to Shibuya, 2 min walk"},
        ],
        "dubai": [
            {"name": "Burj Khalifa Base", "best_time": "5:30 PM - 7:00 PM", "why": "Golden sunset light on the world's tallest building", "how": "Metro Red Line to Burj Khalifa/Dubai Mall"},
            {"name": "Al Fahidi Historic District", "best_time": "6:30 AM - 8:00 AM", "why": "Old Dubai wind towers in soft morning light", "how": "Taxi to Al Fahidi, 15 min from Downtown"},
        ],
        "jaipur": [
            {"name": "Hawa Mahal", "best_time": "6:30 AM - 8:00 AM", "why": "Pink sandstone glows in morning light with no crowds", "how": "Auto from any part of city, 10-20 min"},
            {"name": "Amber Fort", "best_time": "6:00 AM - 7:30 AM", "why": "Misty hills and fort walls in golden sunrise", "how": "Bus or auto from Jaipur city, 11 km, 25 min"},
        ],
        "agra": [
            {"name": "Taj Mahal East Gate", "best_time": "6:00 AM - 7:30 AM", "why": "Sunrise reflection in the central pool is world-famous", "how": "Auto or taxi from Agra Cantt station, 15 min"},
            {"name": "Mehtab Bagh", "best_time": "5:30 PM - 7:00 PM", "why": "Sunset view of Taj Mahal from across the Yamuna", "how": "Auto from Taj Mahal, 2 km, 10 min"},
        ],
        "manali": [
            {"name": "Solang Valley", "best_time": "6:00 AM - 8:00 AM", "why": "Snow-capped peaks in morning golden light", "how": "Taxi from Manali bus stand, 14 km, 30 min"},
            {"name": "Hadimba Temple", "best_time": "6:30 AM - 8:00 AM", "why": "Ancient wooden temple surrounded by deodar forest", "how": "Walk from Mall Road, 2 km, 20 min"},
        ],
        "shimla": [
            {"name": "The Ridge", "best_time": "6:00 AM - 7:30 AM", "why": "Panoramic Himalayan views in clear morning air", "how": "Walk from Shimla bus stand, 10 min uphill"},
            {"name": "Jakhu Temple", "best_time": "5:30 PM - 7:00 PM", "why": "Sunset over the hills with the giant Hanuman statue", "how": "Ropeway from Cart Road or trek, 2.5 km"},
        ],
        "rishikesh": [
            {"name": "Laxman Jhula", "best_time": "6:00 AM - 7:30 AM", "why": "Suspension bridge over Ganga in morning mist", "how": "Auto from Rishikesh bus stand, 5 km, 15 min"},
            {"name": "Triveni Ghat", "best_time": "6:00 AM - 7:00 AM", "why": "Ganga Aarti and sunrise reflections on the holy river", "how": "Walk from Rishikesh center, 10 min"},
        ],
        "goa": [
            {"name": "Palolem Beach", "best_time": "6:00 AM - 7:30 AM", "why": "Crescent beach with fishing boats in sunrise light", "how": "Taxi from Margao, 38 km, 45 min"},
            {"name": "Chapora Fort", "best_time": "5:30 PM - 7:00 PM", "why": "Iconic sunset view over Vagator and Arabian Sea", "how": "Scooter or taxi from Mapusa, 10 km, 20 min"},
        ],
        "varanasi": [
            {"name": "Dashashwamedh Ghat", "best_time": "5:30 AM - 7:00 AM", "why": "Sunrise boat ride with ghats and temples in golden light", "how": "Auto to Godaulia, walk to ghat, 5 min"},
            {"name": "Assi Ghat", "best_time": "5:30 PM - 7:00 PM", "why": "Evening Ganga Aarti with lamps and devotees", "how": "Auto from Varanasi Junction, 5 km, 15 min"},
        ],
        "sydney": [
            {"name": "Sydney Opera House", "best_time": "6:00 AM - 7:30 AM", "why": "Sunrise over the harbour with the iconic shells", "how": "Train to Circular Quay, 5 min walk"},
            {"name": "Bondi Beach", "best_time": "5:30 PM - 7:00 PM", "why": "Golden sunset over the Pacific with surfers", "how": "Bus 333 from CBD, 30 min"},
        ],
    }

    spots = CITY_SPOTS.get(city_lower, [])

    # Fuzzy match for partial city names
    if not spots:
        for key in CITY_SPOTS:
            if key in city_lower or city_lower in key:
                spots = CITY_SPOTS[key]
                break

    return {"score": score, "golden_hour": golden, "tips": tips, "spots": spots}

def get_pet_safety(temp, description, wind):
    desc = description.lower()
    tips = []
    alert = None

    if temp >= 40:
        alert = {"level": "critical", "msg": "DANGER: Do NOT walk your pet outside. Pavement can burn paws at this temperature!"}
        tips.append({"icon": "🐾", "tip": "Paw burn risk is extreme. Keep pets indoors with AC or fans."})
        tips.append({"icon": "💧", "tip": "Ensure fresh cold water is always available. Pets dehydrate faster than humans."})
        tips.append({"icon": "🌡️", "tip": "Watch for heatstroke signs: excessive panting, drooling, lethargy."})
    elif temp >= 32:
        alert = {"level": "warning", "msg": "Hot pavement warning. Walk pets only in early morning or after sunset."}
        tips.append({"icon": "🐕", "tip": "Walk dogs before 8am or after 7pm when pavement is cooler."})
        tips.append({"icon": "💧", "tip": "Carry water for your pet on every walk."})
        tips.append({"icon": "🐾", "tip": "Test pavement with your hand — if too hot for 5 seconds, it's too hot for paws."})
    elif temp <= 0:
        alert = {"level": "warning", "msg": "Freezing conditions. Limit outdoor time for pets, especially small breeds."}
        tips.append({"icon": "🧥", "tip": "Small and short-haired dogs need a coat in freezing weather."})
        tips.append({"icon": "🐾", "tip": "Wipe paws after walks to remove ice, salt, and chemicals."})
        tips.append({"icon": "🏠", "tip": "Keep outdoor time short. Watch for shivering — a sign of hypothermia."})
    elif temp <= 10:
        tips.append({"icon": "🧥", "tip": "Consider a pet jacket for small or elderly dogs in cool weather."})
        tips.append({"icon": "🐾", "tip": "Walks are fine but keep them shorter than usual."})
    elif "rain" in desc or "drizzle" in desc:
        tips.append({"icon": "🌂", "tip": "Use a pet raincoat for walks. Dry your pet thoroughly after coming inside."})
        tips.append({"icon": "🐕", "tip": "Avoid muddy areas — mud can hide sharp objects that hurt paws."})
    elif "thunder" in desc or "storm" in desc:
        alert = {"level": "warning", "msg": "Thunderstorm detected. Keep pets indoors — thunder causes extreme anxiety."}
        tips.append({"icon": "🏠", "tip": "Keep pets indoors. Close windows and curtains to muffle thunder sounds."})
        tips.append({"icon": "🐕", "tip": "Stay calm around your pet — they sense your anxiety. Use calming music."})
    elif wind >= 50:
        tips.append({"icon": "💨", "tip": "Strong winds can startle pets. Keep them on a leash at all times."})
        tips.append({"icon": "🐕", "tip": "Avoid open areas during high winds. Debris can injure pets."})
    else:
        tips.append({"icon": "✅", "tip": "Great weather for a walk! Keep your pet hydrated and on a leash."})
        tips.append({"icon": "🐕", "tip": "Perfect conditions for outdoor play and exercise with your pet."})

    return {"alert": alert, "tips": tips}


def get_plant_care(temp, humidity, description):
    desc = description.lower()
    tips = []
    water_today = True
    frost_warning = False

    if "rain" in desc or "drizzle" in desc or "shower" in desc:
        water_today = False
        tips.append({"icon": "🌧️", "tip": "Skip watering today — natural rain is doing the job for you."})
        tips.append({"icon": "🌱", "tip": "Check drainage to prevent root rot from excess water."})
    elif humidity >= 80:
        water_today = False
        tips.append({"icon": "💧", "tip": "High humidity — reduce watering frequency to avoid fungal diseases."})
        tips.append({"icon": "🍄", "tip": "Watch for mold or mildew on leaves. Improve air circulation around plants."})
    elif temp >= 38:
        tips.append({"icon": "💧", "tip": "Water plants in the early morning or evening to prevent evaporation."})
        tips.append({"icon": "🌿", "tip": "Move potted plants to shade. Direct sun at this temperature can scorch leaves."})
        tips.append({"icon": "🌡️", "tip": "Mulch around plants to retain soil moisture in extreme heat."})
    elif temp <= 2:
        frost_warning = True
        water_today = False
        tips.append({"icon": "❄️", "tip": "Frost warning! Cover sensitive plants with cloth or bring indoors tonight."})
        tips.append({"icon": "🌱", "tip": "Do not water today — wet soil freezes and damages roots."})
        tips.append({"icon": "🏠", "tip": "Move potted plants indoors or to a sheltered area immediately."})
    elif temp <= 10:
        tips.append({"icon": "🥶", "tip": "Cold weather slows plant growth. Reduce watering and fertilizing."})
        tips.append({"icon": "🌱", "tip": "Protect tropical plants from cold drafts near windows."})
    else:
        tips.append({"icon": "💧", "tip": "Water plants when top inch of soil feels dry. Check moisture before watering."})
        tips.append({"icon": "🌱", "tip": "Good growing conditions today. Great time for repotting or pruning."})

    if "sunny" in desc or "clear" in desc:
        tips.append({"icon": "☀️", "tip": "Excellent sunlight today. Rotate sun-loving plants to face the light."})
    if "fog" in desc or "mist" in desc:
        tips.append({"icon": "🌫️", "tip": "Foggy conditions provide natural moisture. Outdoor plants will benefit."})

    return {"water_today": water_today, "frost_warning": frost_warning, "tips": tips}


def get_weather_type(description):
    desc = description.lower()
    if "thunder" in desc or "storm" in desc: return "thunder"
    if "snow" in desc or "blizzard" in desc: return "snow"
    if "rain" in desc or "drizzle" in desc or "shower" in desc: return "rain"
    if "fog" in desc or "mist" in desc: return "fog"
    if "cloud" in desc or "overcast" in desc: return "cloudy"
    if "sunny" in desc or "clear" in desc: return "sunny"
    return "default"


CITY_BACKGROUNDS = {
    "paris": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=1600&auto=format&fit=crop",
    "london": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=1600&auto=format&fit=crop",
    "new york": "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=1600&auto=format&fit=crop",
    "tokyo": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=1600&auto=format&fit=crop",
    "dubai": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=1600&auto=format&fit=crop",
    "sydney": "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?w=1600&auto=format&fit=crop",
    "mumbai": "https://images.unsplash.com/photo-1570168007204-dfb528c6958f?w=1600&auto=format&fit=crop",
    "rome": "https://images.unsplash.com/photo-1552832230-c0197dd311b5?w=1600&auto=format&fit=crop",
    "barcelona": "https://images.unsplash.com/photo-1583422409516-2895a77efded?w=1600&auto=format&fit=crop",
    "singapore": "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?w=1600&auto=format&fit=crop",
    "istanbul": "https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?w=1600&auto=format&fit=crop",
    "cairo": "https://images.unsplash.com/photo-1572252009286-268acec5ca0a?w=1600&auto=format&fit=crop",
    "moscow": "https://images.unsplash.com/photo-1513326738677-b964603b136d?w=1600&auto=format&fit=crop",
    "beijing": "https://images.unsplash.com/photo-1508804185872-d7badad00f7d?w=1600&auto=format&fit=crop",
    "los angeles": "https://images.unsplash.com/photo-1534190760961-74e8c1c5c3da?w=1600&auto=format&fit=crop",
    "chicago": "https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?w=1600&auto=format&fit=crop",
    "toronto": "https://images.unsplash.com/photo-1517090504586-fde19ea6066f?w=1600&auto=format&fit=crop",
    "amsterdam": "https://images.unsplash.com/photo-1534351590666-13e3e96b5017?w=1600&auto=format&fit=crop",
    "berlin": "https://images.unsplash.com/photo-1560969184-10fe8719e047?w=1600&auto=format&fit=crop",
    "bangkok": "https://images.unsplash.com/photo-1508009603885-50cf7c579365?w=1600&auto=format&fit=crop",
}


@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")

    weather = None
    forecast = None
    ai_analysis = None
    outfit = None
    mood = None
    alerts = []
    aqi = None
    weather_type = "default"
    city_bg = None
    is_favorite = False
    city = request.args.get("city")

    if city:
        try:
            data = get_cached_weather(city)
            if not data:
                url = f"https://wttr.in/{city}?format=j1"
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                data = response.json()
                set_cached_weather(city, data)
            current = data["current_condition"][0]

            temp = float(current["temp_C"])
            humidity = float(current["humidity"])
            wind = float(current["windspeedKmph"])
            feels_like = float(current["FeelsLikeC"])
            uv_index = int(current.get("uvIndex", 0))
            visibility = current.get("visibility", "N/A")
            pressure = float(current.get("pressure", 1015))
            description = current["weatherDesc"][0]["value"]

            prediction = predict_weather(temp, humidity, wind, pressure)

            weather = {
                "city": city.title(),
                "temp": temp,
                "humidity": humidity,
                "wind": wind,
                "pressure": pressure,
                "feels_like": feels_like,
                "uv_index": uv_index,
                "visibility": visibility,
                "description": description,
                "prediction": prediction
            }

            # 3-day forecast
            forecast = []
            days = ["Today", "Tomorrow", "Day After"]
            for i, day_data in enumerate(data.get("weather", [])[:3]):
                hourly = day_data["hourly"]
                avg_temp = sum(float(h["tempC"]) for h in hourly) / len(hourly)
                avg_humidity = sum(float(h["humidity"]) for h in hourly) / len(hourly)
                desc = day_data["hourly"][4]["weatherDesc"][0]["value"]
                forecast.append({
                    "day": days[i],
                    "date": day_data["date"],
                    "max_temp": float(day_data["maxtempC"]),
                    "min_temp": float(day_data["mintempC"]),
                    "avg_temp": round(avg_temp, 1),
                    "humidity": round(avg_humidity),
                    "description": desc
                })

            # AI features
            ai_analysis = get_ai_analysis(temp, humidity, wind, description)
            outfit = get_outfit(temp, description)
            mood = get_mood(temp, description)
            alerts = get_alerts(temp, wind, description, humidity)
            weather_type = get_weather_type(description)
            city_bg = CITY_BACKGROUNDS.get(city.lower())

            # AQI
            try:
                area = data["nearest_area"][0]
                lat = float(area["latitude"])
                lon = float(area["longitude"])
                aqi = get_aqi(lat, lon)
            except Exception:
                aqi = None
                lat = lon = None

            health = get_health_risks(temp, humidity, uv_index, wind, description, aqi["level"] if aqi else None)
            farming = get_farming_intel(temp, humidity, wind, description)
            energy = get_energy_tips(temp, description, uv_index)
            productivity = get_productivity(temp, humidity, description)
            food = get_food_recommendation(temp, description)
            photography = get_photography_tips(temp, description, uv_index, city)
            if not photography["spots"] and lat and lon:
                photography["spots"] = get_photo_spots(lat, lon, city)
            pet = get_pet_safety(temp, description, wind)
            plant = get_plant_care(temp, humidity, description)

            # Save history
            with get_db() as conn:
                conn.execute("INSERT INTO search_history(username, city) VALUES(?, ?)", (session["user"], city.title()))
                conn.execute("""
                    DELETE FROM search_history WHERE id NOT IN (
                        SELECT id FROM search_history WHERE username=?
                        ORDER BY searched_at DESC LIMIT 10
                    ) AND username=?
                """, (session["user"], session["user"]))
                conn.commit()

            is_favorite = False
            with get_db() as conn:
                fav = conn.execute(
                    "SELECT id FROM user_favorites WHERE username=? AND city=?",
                    (session["user"], city.title())
                ).fetchone()
                is_favorite = fav is not None

        except Exception as e:
            flash(f'Could not find weather for "{city}". Please check the city name.', 'error')
            health = farming = energy = productivity = food = photography = pet = plant = None

    else:
        health = farming = energy = productivity = food = photography = pet = plant = None

    with get_db() as conn:
        history = conn.execute(
            "SELECT DISTINCT city FROM search_history WHERE username=? ORDER BY searched_at DESC LIMIT 8",
            (session["user"],)
        ).fetchall()
        favorites = conn.execute(
            "SELECT city FROM user_favorites WHERE username=? ORDER BY added_at DESC",
            (session["user"],)
        ).fetchall()

    return render_template("index.html",
        weather=weather, forecast=forecast, ai_analysis=ai_analysis,
        outfit=outfit, mood=mood, alerts=alerts, aqi=aqi,
        health=health, farming=farming, energy=energy, productivity=productivity,
        food=food, photography=photography, pet=pet, plant=plant,
        weather_type=weather_type, city_bg=city_bg,
        username=session["user"], city=city,
        history=[row["city"] for row in history],
        favorites=[row["city"] for row in favorites],
        is_favorite=is_favorite
    )


@app.route("/chat", methods=["POST"])
def chat():
    if "user" not in session:
        return jsonify({"reply": "Please log in first."})

    data = request.get_json()
    msg = data.get("message", "").lower().strip()
    weather = data.get("weather", {})

    temp = float(weather.get("temp", 20))
    humidity = float(weather.get("humidity", 50))
    wind = float(weather.get("wind", 10))
    desc = weather.get("desc", "").lower()
    city = weather.get("city", "your city")
    uv = int(weather.get("uv", 0))

    def reply(text): return jsonify({"reply": text})

    feels_like = float(weather.get("feels_like", temp))

    # ---- OUTFIT / WHAT TO WEAR ----
    if any(w in msg for w in ["wear", "wearing", "outfit", "dress", "clothes", "clothing",
                               "what should i", "what to wear", "what do i wear",
                               "jacket", "coat", "shirt", "shorts", "boots", "shoes",
                               "umbrella", "scarf", "gloves", "hat", "cap", "hoodie",
                               "t-shirt", "sweater", "raincoat", "sunglasses", "sandals"]):
        o = get_outfit(temp, desc)
        detail = ""
        if temp >= 35:
            detail = f"It's very hot ({temp}°C) in {city}. Avoid dark colors — they absorb heat. Wear breathable fabrics like cotton or linen. Don't forget sunscreen SPF 30+."
        elif temp >= 28:
            detail = f"It's warm ({temp}°C) in {city}. Light casual clothes work great. Sunglasses and a cap are a good idea."
        elif temp >= 20:
            detail = f"It's pleasant ({temp}°C) in {city}. A light layer like a hoodie or denim jacket is perfect."
        elif temp >= 10:
            detail = f"It's cool ({temp}°C) in {city}. Layer up — a warm jacket, jeans, and closed shoes are ideal."
        elif temp >= 0:
            detail = f"It's cold ({temp}°C) in {city}. Wear a heavy coat, thermal underlayer, scarf, and gloves."
        else:
            detail = f"It's freezing ({temp}°C) in {city}! Full winter gear — insulated coat, thermal layers, waterproof boots, hat and gloves are essential."
        if "rain" in desc or "drizzle" in desc or "shower" in desc:
            detail += " It's also raining — carry a waterproof jacket or umbrella and wear waterproof shoes."
        if "snow" in desc:
            detail += " Snow is falling — wear waterproof insulated boots and avoid cotton as it gets wet quickly."
        if "thunder" in desc or "storm" in desc:
            detail += " There's a storm — if you must go out, wear a raincoat and avoid metal accessories."
        if uv >= 8:
            detail += f" UV Index is very high ({uv}) — wear a hat and apply SPF 50+ sunscreen."
        return reply(f"{o['icon']} Outfit Recommendation for {city}:\n\n👔 Style: {o['title']}\n\n{detail}\n\n💡 Tip: {o['tip']}")

    # ---- GOING OUTSIDE ----
    if any(w in msg for w in ["go outside", "outside", "go out", "step out"]):
        if "thunder" in desc or "storm" in desc:
            return reply(f"⛈️ I'd strongly advise against going outside right now in {city}. There's an active thunderstorm with lightning risk. Stay safe indoors!")
        if temp >= 40:
            return reply(f"🔥 It's {temp}°C in {city} — dangerously hot. Going outside risks heatstroke. If you must, carry water and stay in shade.")
        if "rain" in desc:
            return reply(f"🌧️ It's raining in {city} right now. Carry an umbrella and wear waterproof shoes if you're heading out.")
        if temp <= 0:
            return reply(f"🧊 Freezing conditions in {city} ({temp}°C). Bundle up with heavy layers, gloves, and a hat before going out.")
        return reply(f"✅ Weather in {city} looks fine for going outside! It's {temp}°C with {desc}. Enjoy your time out!")

    # Driving / travel
    if any(w in msg for w in ["drive", "driving", "travel", "road", "safe to drive"]):
        if "thunder" in desc or "storm" in desc:
            return reply(f"⚠️ Driving in {city} is risky right now due to thunderstorm conditions. Lightning and slippery roads are dangerous. Delay travel if possible.")
        if "snow" in desc or "blizzard" in desc:
            return reply(f"❄️ Snowfall detected in {city}. Roads may be icy. Drive slowly, use winter tires, and keep extra distance from vehicles ahead.")
        if "fog" in desc or "mist" in desc:
            return reply(f"🌫️ Foggy conditions in {city} reduce visibility. Use fog lights, drive slowly, and avoid highways if possible.")
        if wind >= 60:
            return reply(f"💨 Strong winds ({wind} km/h) in {city} may affect high-sided vehicles. Drive carefully and avoid exposed roads.")
        if "rain" in desc:
            return reply(f"🌧️ It's raining in {city}. Roads may be slippery. Reduce speed and increase following distance.")
        return reply(f"✅ Driving conditions in {city} are generally safe right now. It's {temp}°C with {desc}. Drive safely!")

    # Jogging / exercise
    if any(w in msg for w in ["jog", "jogging", "run", "running", "exercise", "workout", "walk", "walking"]):
        if temp >= 38:
            return reply(f"🔥 {temp}°C in {city} is too hot for outdoor exercise. Risk of heatstroke is high. Work out indoors or wait until evening.")
        if temp <= 0:
            return reply(f"🥶 It's {temp}°C in {city} — very cold for outdoor exercise. Warm up thoroughly and wear thermal layers if you go out.")
        if "rain" in desc or "thunder" in desc:
            return reply(f"🌧️ It's {desc} in {city}. Outdoor exercise is not ideal. Consider an indoor workout today.")
        if temp >= 28 and humidity >= 70:
            return reply(f"😓 High heat and humidity in {city} ({temp}°C, {humidity}% humidity). Exercise early morning before 8am or after 6pm. Stay hydrated!")
        return reply(f"🏃 Great conditions for a jog in {city}! It's {temp}°C with {desc}. Stay hydrated and enjoy your run!")

    # Studying
    if any(w in msg for w in ["study", "studying", "focus", "concentrate", "work", "productive"]):
        prod = get_productivity(temp, humidity, desc)
        return reply(f"📚 Productivity forecast for {city}: Score {prod['score']}/100. Mood: {prod['mood']}. Best study time: {prod['study_time']}. {prod['tips'][0] if prod['tips'] else ''}")

    # Headache / migraine
    if any(w in msg for w in ["headache", "migraine", "head", "pain"]):
        if ("thunder" in desc or "storm" in desc) or (humidity >= 80):
            return reply(f"🧠 Yes, weather in {city} may trigger migraines. Pressure changes and high humidity ({humidity}%) are known triggers. Stay hydrated, rest in a dark room, and take your medication if needed.")
        return reply(f"🧠 Current weather in {city} ({temp}°C, {humidity}% humidity) is not a strong migraine trigger. However, stay hydrated and avoid screen glare.")

    # Sleep
    if any(w in msg for w in ["sleep", "sleeping", "rest", "nap"]):
        prod = get_productivity(temp, humidity, desc)
        return reply(f"😴 Sleep quality forecast for {city}: {prod['sleep']}. {('High temperature may disrupt sleep — keep room cool.' if temp >= 30 else 'Conditions are suitable for good rest tonight.')}")

    # UV / sunscreen
    if any(w in msg for w in ["uv", "sunscreen", "sunburn", "spf", "sun"]):
        if uv >= 8:
            return reply(f"☀️ UV Index in {city} is {uv} — Very High! Apply SPF 50+ sunscreen, wear sunglasses and a hat. Avoid direct sun between 10am–4pm.")
        elif uv >= 6:
            return reply(f"🌤️ UV Index is {uv} in {city}. Moderate-high risk. Use SPF 30+ and reapply every 2 hours outdoors.")
        elif uv >= 3:
            return reply(f"🌤️ UV Index is {uv} in {city}. Low-moderate. SPF 15 is sufficient for short outdoor exposure.")
        return reply(f"✅ UV Index is low ({uv}) in {city} today. Minimal sun protection needed.")

    # Temperature query
    if any(w in msg for w in ["temperature", "temp", "hot", "cold", "warm", "cool", "how warm", "how cold"]):
        return reply(f"🌡️ Current temperature in {city} is {temp}°C. Feels like {weather.get('feels_like', temp)}°C. Conditions: {desc}.")

    # Rain query
    if any(w in msg for w in ["rain", "raining", "umbrella", "wet"]):
        if "rain" in desc or "drizzle" in desc or "shower" in desc:
            return reply(f"🌧️ Yes, it's currently {desc} in {city}. Carry an umbrella and wear waterproof footwear.")
        return reply(f"☀️ No rain currently in {city}. Conditions are {desc}. But keep an eye on the 3-day forecast!")

    # General weather
    if any(w in msg for w in ["weather", "forecast", "today", "conditions", "how is", "what's the"]):
        return reply(f"🌍 Current weather in {city}: {temp}°C, {desc}. Humidity: {humidity}%, Wind: {wind} km/h. UV Index: {uv}. Overall conditions look {'good' if temp < 35 and 'thunder' not in desc else 'challenging'} today.")

    # Farming
    if any(w in msg for w in ["farm", "crop", "plant", "water", "irrigat", "harvest", "soil"]):
        tips = get_farming_intel(temp, humidity, wind, desc)
        return reply(f"🌾 Farming intel for {city}: {tips[0]['tip']} {tips[1]['tip'] if len(tips) > 1 else ''}")

    # Energy
    if any(w in msg for w in ["energy", "solar", "electricity", "power", "ac", "heater"]):
        tips = get_energy_tips(temp, desc, uv)
        return reply(f"⚡ Energy tip for {city}: {tips[0]['tip']}")

    # Food recommendation
    if any(w in msg for w in ["food", "eat", "drink", "hungry", "meal", "cook", "coffee", "snack", "recipe"]):
        f = get_food_recommendation(temp, desc)
        items = ", ".join([i["icon"] + " " + i["name"] for i in f["items"]])
        return reply(f"{f['emoji']} {f['title']} for {city}:\n\n{items}\n\nPerfect choices for {desc} weather at {temp}\u00b0C!")

    # Pet safety
    if any(w in msg for w in ["pet", "dog", "cat", "walk dog", "paw", "animal"]):
        p = get_pet_safety(temp, desc, wind)
        alert_msg = ("\n\u26a0\ufe0f " + p["alert"]["msg"]) if p["alert"] else ""
        tip = p["tips"][0]["tip"] if p["tips"] else ""
        return reply(f"\ud83d\udc3e Pet Safety for {city}:{alert_msg}\n\n{tip}")

    # Plant care
    if any(w in msg for w in ["plant", "water plant", "garden", "flower", "soil", "frost"]):
        pl = get_plant_care(temp, humidity, desc)
        water = "Yes, water your plants today." if pl["water_today"] else "Skip watering today."
        frost = " FROST WARNING active!" if pl["frost_warning"] else ""
        tip = pl["tips"][0]["tip"] if pl["tips"] else ""
        return reply(f"\ud83c\udf31 Plant Care for {city}:{frost}\n\n\ud83d\udca7 {water}\n\n{tip}")

    # Photography
    if any(w in msg for w in ["photo", "photography", "camera", "shoot", "golden hour", "sunset", "picture"]):
        ph = get_photography_tips(temp, desc, uv)
        tip = ph["tips"][0]["tip"] if ph["tips"] else ""
        return reply(f"\ud83d\udcf8 Photography Score for {city}: {ph['score']}/100\n\n\ud83c\udf05 Golden Hour: {ph['golden_hour']}\n\n{tip}")

    # Greeting
    if any(w in msg for w in ["hello", "hi", "hey", "good morning", "good evening", "what can you do", "help"]):
        return reply(f"👋 Hello! I'm NEBULA AI for {city}. Ask me:\n• 'What should I wear?'\n• 'What food suits this weather?'\n• 'Is it safe to walk my dog?'\n• 'Should I water my plants?'\n• 'Best time for photography?'\n• 'Can I go jogging?'\n• 'Is it safe to drive?'")

    return reply(f"🤖 I'm not sure about that. Try asking me: 'Can I go outside?', 'Is it good for jogging?', 'Will it rain?', or 'What's the UV risk?' for {city}.")


@app.route("/favorite", methods=["POST"])
def toggle_favorite():
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 401
    city = request.get_json().get("city", "").strip().title()
    if not city:
        return jsonify({"error": "No city"}), 400
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM user_favorites WHERE username=? AND city=?",
            (session["user"], city)
        ).fetchone()
        if existing:
            conn.execute("DELETE FROM user_favorites WHERE username=? AND city=?", (session["user"], city))
            conn.commit()
            return jsonify({"status": "removed", "city": city})
        else:
            conn.execute("INSERT INTO user_favorites(username, city) VALUES(?, ?)", (session["user"], city))
            conn.commit()
            return jsonify({"status": "added", "city": city})


@app.route("/profile")
def profile():
    if "user" not in session:
        return redirect("/login")
    with get_db() as conn:
        user = conn.execute("SELECT created_at FROM users WHERE username=?", (session["user"],)).fetchone()
        total_searches = conn.execute(
            "SELECT COUNT(*) as cnt FROM search_history WHERE username=?", (session["user"],)
        ).fetchone()["cnt"]
        top_cities = conn.execute(
            "SELECT city, COUNT(*) as cnt FROM search_history WHERE username=? GROUP BY city ORDER BY cnt DESC LIMIT 5",
            (session["user"],)
        ).fetchall()
        favorites = conn.execute(
            "SELECT city, added_at FROM user_favorites WHERE username=? ORDER BY added_at DESC",
            (session["user"],)
        ).fetchall()
        recent = conn.execute(
            "SELECT city, searched_at FROM search_history WHERE username=? ORDER BY searched_at DESC LIMIT 10",
            (session["user"],)
        ).fetchall()
    return render_template("profile.html",
        username=session["user"],
        created_at=user["created_at"] if user and user["created_at"] else "N/A",
        total_searches=total_searches,
        top_cities=top_cities,
        favorites=favorites,
        recent=recent
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("register.html")
        with get_db() as conn:
            if conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone():
                flash("Username already taken. Please choose another.", "error")
                return render_template("register.html")
            conn.execute("INSERT INTO users(username,password) VALUES(?,?)", (username, hash_password(password)))
            conn.commit()
        flash("Account created! Please log in.", "success")
        return redirect("/login")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE username=? AND password=?",
                (username, hash_password(password))
            ).fetchone()
        if user:
            session["user"] = username
            return redirect("/")
        else:
            flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
