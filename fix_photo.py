import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

new_func = '''def get_photography_tips(temp, description, uv_index, city=""):
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

'''

# Replace the old function
pattern = r'def get_photography_tips\(.*?\)\n.*?return \{.*?\}\n\n\n'
new_content = re.sub(pattern, new_func, content, flags=re.DOTALL)

if new_content == content:
    print("Pattern not matched - trying line-based replacement")
    lines = content.split('\n')
    start = None
    end = None
    for i, line in enumerate(lines):
        if 'def get_photography_tips' in line:
            start = i
        if start and i > start and line.startswith('def get_pet_safety'):
            end = i
            break
    if start and end:
        new_lines = lines[:start] + new_func.split('\n') + lines[end:]
        new_content = '\n'.join(new_lines)
        print(f"Replaced lines {start} to {end}")
    else:
        print(f"Could not find boundaries: start={start}, end={end}")
else:
    print("Regex replacement successful")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("Done")
