from flask import Flask, Response, jsonify
import fastf1
from datetime import datetime, timezone, timedelta
import os
import requests
from cachetools import cached, TTLCache
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timezone
from babel.dates import format_date
from flask_cors import CORS

CORS(app)
app = Flask(__name__)

CACHE_DIR = 'f1_cache'
os.makedirs(CACHE_DIR, exist_ok=True)
try:
    fastf1.Cache.enable_cache(CACHE_DIR)
except Exception as e:
    print(f"Warning: Could not enable FastF1 cache: {e}")

api_cache = TTLCache(maxsize=5, ttl=3600)
driver_cache = TTLCache(maxsize=5, ttl=3600)
constructor_cache = TTLCache(maxsize=5, ttl=3600)
winner_cache = TTLCache(maxsize=5, ttl=3600) 
cal_cache = TTLCache(maxsize=10, ttl=86400)

def nationality_to_flag(nationality):
    flags = {
        "British": "🇬🇧", "German": "🇩🇪", "Dutch": "🇳🇱", "Monegasque": "🇲🇨",
        "Mexican": "🇲🇽", "Spanish": "🇪🇸", "French": "🇫🇷", "Finnish": "🇫🇮",
        "Canadian": "🇨🇦", "Australian": "🇦🇺", "Japanese": "🇯🇵", "Chinese": "🇨🇳",
        "Thai": "🇹🇭", "American": "🇺🇸", "Italian": "🇮🇹", "Austrian": "🇦🇹",
        "Brazilian": "🇧🇷", "Swiss": "🇨🇭", "New Zealander": "🇳🇿"
    }
    if not nationality:
        return "🏳️"
    flag = flags.get(nationality)
    if not flag:
        print(f"⚠️ Unknown nationality: '{nationality}'")
        return "🏳️"
    return flag

def location_to_flag(country):
    flags = {
        
    "Bahrain": "🇧🇭", "Saudi Arabia": "🇸🇦","Australia": "🇦🇺",
    "Japan": "🇯🇵", "China": "🇨🇳","United States": "🇺🇸",
    "Italy": "🇮🇹","Monaco": "🇲🇨","Canada": "🇨🇦", 
    "Spain": "🇪🇸","Austria": "🇦🇹","United Kingdom": "🇬🇧",
    "Hungary": "🇭🇺","Belgium": "🇧🇪","Netherlands": "🇳🇱",
    "Azerbaijan": "🇦🇿","Singapore": "🇸🇬","Mexico": "🇲🇽",
    "Brazil": "🇧🇷","Qatar": "🇶🇦","United Arab Emirates": "🇦🇪",  
    }
    return flags.get(country, "🏁")


TRACK_NAMES = {
    "Bahrain GP": "Bahrain International Circuit",
    "Saudi Arabian GP": "Jeddah Street Circuit",
    "Australian GP": "Albert Park Circuit",
    "Japanese GP": "Suzuka Circuit",
    "Chinese GP": "Shanghai International Circuit",
    "Miami GP": "Miami International Autodrome",
    "Emilia Romagna GP": "Imola Circuit",
    "Monaco GP": "Circuit de Monaco",
    "Canadian GP": "Circuit Gilles Villeneuve",
    "Spanish GP": "Circuit de Barcelona-Catalunya",
    "Austrian GP": "Red Bull Ring",
    "British GP": "Silverstone Circuit",
    "Hungarian GP": "Hungaroring",
    "Belgian GP": "Circuit de Spa-Francorchamps",
    "Dutch GP": "Circuit Zandvoort",
    "Italian GP": "Monza Circuit",
    "Azerbaijan GP": "Baku City Circuit",
    "Singapore GP": "Marina Bay Street Circuit",
    "United States GP": "Circuit of the Americas",
    "Mexico GP": "Autódromo Hermanos Rodríguez",
    "Brazilian GP": "Interlagos Circuit",
    "Las Vegas GP": "Las Vegas Street Circuit",
    "Qatar GP": "Lusail International Circuit",
    "Abu Dhabi GP": "Yas Marina Circuit"
}


CIRCUIT_COORDINATES = {
    "Bahrain": (26.0325, 50.5106),
    "Saudi Arabia": (21.6319, 39.1044),
    "Australia": (-37.8497, 144.968),
    "Japan": (34.8431, 136.5419),
    "China": (31.3389, 121.2197),
    "Miami": (25.9580, -80.2389),
    "Emilia Romagna": (44.3442, 11.7166),
    "Monaco": (43.7347, 7.4206),
    "Canada": (45.5000, -73.5228),
    "Spain": (41.5700, 2.2611),
    "Austria": (47.2197, 14.7647),
    "UK": (52.0786, -1.0169),
    "Hungary": (47.5789, 19.2486),
    "Belgium": (50.4372, 5.9714),
    "Netherlands": (52.3889, 4.5400),
    "Italy": (45.6156, 9.2811),
    "Azerbaijan": (40.3725, 49.8533),
    "Singapore": (1.2914, 103.8644),
    "USA": (30.1328, -97.6411),
    "Mexico": (19.4042, -99.0907),
    "Brazil": (-23.7036, -46.6997),
    "Las Vegas": (36.1147, -115.1728),
    "Qatar": (25.4865, 51.4536),
    "Abu Dhabi": (24.4672, 54.6031),
}

DEFAULT_WEATHER = "🌤️ ?°C"
ERGAST_TIMEOUT = 10


@cached(cache=driver_cache)
def fetch_top_driver_standings(limit=3):
    url = 'https://api.jolpi.ca/ergast/f1/2025/driverstandings.json'
    try:
        response = requests.get(url, timeout=ERGAST_TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Driver standings fetch error: {e}")
        return []

    data = response.json()
    standings_list = data.get('MRData', {}).get('StandingsTable', {}).get('StandingsLists', [])
    if not standings_list or not standings_list[0].get('DriverStandings'):
        return []

    standings = []
    drivers_data = standings_list[0]['DriverStandings']
    for driver in drivers_data[:limit]:
        driver_info = driver.get('Driver', {})
        code = driver_info.get('code', driver_info.get('familyName', ''))
        points = driver.get('points', '0')
        nationality = driver_info.get('nationality', '')
        flag = nationality_to_flag(nationality)
        standings.append(f"{flag} {code} {points}pts")

    return " • ".join([f"{i+1}.{d}" for i, d in enumerate(standings)])

    
@cached(cache=constructor_cache)
def fetch_top_constructor_standings(limit=3):
    url = 'https://api.jolpi.ca/ergast/f1/2025/constructorstandings.json'
    try:
        response = requests.get(url, timeout=ERGAST_TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Constructor standings fetch error: {e}")
        return []

    data = response.json()
    constructors_list = data.get('MRData', {}).get('StandingsTable', {}).get('StandingsLists', [])
    if not constructors_list:
        return []

    top_constructors = constructors_list[0].get('ConstructorStandings', [])
    if not top_constructors:
        return []

    result = []
    for constructor in top_constructors[:limit]:
        constructor_info = constructor.get('Constructor', {})
        name = constructor_info.get('name', 'Unknown')
        nationality = constructor_info.get('nationality', '')
        flag = nationality_to_flag(nationality)
        points = constructor.get('points', '0')
        result.append(f"{flag} {name} {points}pts")

    return " • ".join([f"{i+1}.{c}" for i, c in enumerate(result)])


@cached(cache=winner_cache)
def fetch_last_race_winner():
    url = 'https://api.jolpi.ca/ergast/f1/2025/last/results.json'
    try:
        response = requests.get(url, timeout=ERGAST_TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching last race winner: {e}")
        return "N/A"

    data = response.json()
    races = data.get('MRData', {}).get('RaceTable', {}).get('Races', [])
    if not races or not races[0].get('Results'):
        return "N/A"

    race_info = races[0]
    results = race_info['Results']
    if not results:
        return "N/A"

    race_name = race_info.get('raceName', '').replace('Grand Prix', 'GP')
    winner_data = results[0].get('Driver', {})
    driver_code = winner_data.get('code', '???')
    nationality = winner_data.get('nationality', '')
    flag = nationality_to_flag(nationality)

    return f"{flag} {driver_code} ({race_name})"

@cached(cache=api_cache)
def fetch_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        current = data.get("current_weather", {})
        temp = current.get("temperature", "?")
        icon_code = current.get("weathercode", 0)

        weather_icons = {
            0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️", 45: "🌫️", 48: "🌫️",
            51: "🌦️", 53: "🌦️", 55: "🌧️", 61: "🌧️", 63: "🌧️", 65: "🌧️",
            71: "🌨️", 73: "🌨️", 75: "❄️", 95: "⛈️", 96: "⛈️", 99: "⛈️"
        }
        icon = weather_icons.get(icon_code, "🌡️")
        return f"{icon} {temp}°C"
        
    except Exception as e:
        print(f"Weather fetch failed: {e}")
        return DEFAULT_WEATHER
        
def get_track_name(gp_name):
    return TRACK_NAMES.get(gp_name, "Unknown Circuit")

@cached(cache=cal_cache)
def get_season_calendar():
    
    now = datetime.now(timezone.utc)
    schedule = fastf1.get_event_schedule(now.year, include_testing=False)
    calendar = []

    for _, event in schedule.iterrows():
        gp_name = event['EventName'].replace("Grand Prix", "GP")
        location = event.get("Location", "Unknown")
        country = event.get("Country", "Unknown")
        flag = location_to_flag(country)
        circuit = get_track_name(gp_name)

        # Get first and last session dates (non-null)
        session_dates = []
        for i in range(1, 6):
            dt = event.get(f"Session{i}Date")
            if dt and not pandas.isna(dt):
                dt_local = dt.to_pydatetime().astimezone()
                session_dates.append(dt_local)

        if not session_dates:
            continue

        start = min(session_dates)
        end = max(session_dates)

        # Format like "April 11–13"
        if start.month == end.month:
            date_range = f"{start.strftime('%B')} {start.day}–{end.day}"
        else:
            date_range = f"{start.strftime('%b')} {start.day} – {end.strftime('%b')} {end.day}"

        calendar.append({
            "Name": gp_name,
            "Location": location,
            "Circuit": circuit,
            "Country": flag,
            "DateRange": date_range
        })

    return calendar


@cached(cache=api_cache)
def get_next_race_info():
    import pandas
    now = datetime.now(timezone.utc)
    schedule = fastf1.get_event_schedule(now.year, include_testing=False)

    next_event = schedule[schedule['Session5Date'] > now]
    if next_event.empty:
        return {
            "Race": {"Name": "No upcoming race"},
            "Sessions": [],
            "Drivers": "N/A",
            "Constructors": "N/A",
            "Last Winner": "N/A"
        }

    event = next_event.iloc[0]
    event_name_raw = event['EventName']
    gp_name = event_name_raw.replace("Grand Prix", "GP")
    circuit_name = TRACK_NAMES.get(gp_name, "Unknown Circuit")

    location = event.get("Location", "Unknown")
    lat = event.get("LocationLatitude")
    lon = event.get("LocationLongitude")
    country = event.Country    
    location_flag = location_to_flag(country)

    if not lat or not lon:
        coords = CIRCUIT_COORDINATES.get(gp_name.replace(" GP", ""))
        if coords:
            lat, lon = coords

    weather = fetch_weather(lat, lon) if lat and lon else DEFAULT_WEATHER

    # Build session info with status
    session_names = ["FP1", "FP2", "FP3", "Quali", "Race"]
    sessions = []
    current_session = None
    next_session_name = None
    next_session_time = None
    found_next = False

    for i in range(1, 6):
        session_dt = event.get(f"Session{i}Date")
        name = session_names[i - 1]
        if session_dt and not pandas.isna(session_dt):
            start_utc = session_dt.to_pydatetime().astimezone(timezone.utc)
            end_utc = start_utc + timedelta(hours=1.5)  # assume 90 min duration
            start_local = start_utc.astimezone()
            status = "🕓 Upcoming"

            if start_utc <= now <= end_utc:
                status = "🔴 LIVE"
                current_session = f"{status}: {name}"
            elif now > end_utc:
                status = "✅ Completed"
            elif not found_next:
                next_session_name = name
                next_session_time = start_utc
                found_next = True

            sessions.append({
                "name": name,
                "status": status,
                "datetime_utc": start_utc.isoformat(),
                "datetime_local": start_local.strftime('%a %H:%M')
            })

    # Countdown to next session
    if next_session_time:
        delta_next = next_session_time - now
        countdown_next = f"⏱️ {next_session_name} in {delta_next.days}d {delta_next.seconds // 3600}h {(delta_next.seconds // 60) % 60}m"
    else:
        countdown_next = "N/A"

    # Countdown to race
    race_dt = event.get("Session5Date")
    if race_dt and not pandas.isna(race_dt):
        race_utc = race_dt.to_pydatetime().astimezone(timezone.utc)
        if race_utc > now:
            delta_race = race_utc - now
            countdown_race = f"🟩 Race in {delta_race.days}d {delta_race.seconds // 3600}h {(delta_race.seconds // 60) % 60}m"
        else:
            countdown_race = "N/A"
    else:
        countdown_race = "N/A"

    top_drivers = fetch_top_driver_standings()
    top_constructors = fetch_top_constructor_standings()
    last_winner = fetch_last_race_winner()
    Cal = get_season_calendar()

    return {
        "Race": {
            "Name": gp_name,
            "Circuit-Name" : circuit_name,
            "Location": location,
            "Country": location_flag,
            "Weather": weather,
            "CountdownToNextSession": countdown_next,
            "CountdownToRace": countdown_race,
            #"CurrentSession": current_session,
            "NextSession": next_session_name
        },
        "Calender" : {
            "2025 " : Cal
        },
        "Sessions": sessions,
        "Drivers": f"[DRIVER STANDINGS] {top_drivers}",
        "Constructors": f"[CONSTRUCTOR STANDINGS] {top_constructors}",
        "Last Winner": f"[WINNER] {last_winner}"
    }

@app.route("/f1info.json")
def f1info_json():
    try:
        info = get_next_race_info()
        return jsonify(info)
    except Exception as e:
        print(f"ERROR generating F1 JSON data: {e}")
        return jsonify({"error": "Could not retrieve F1 data."}), 500

if __name__ == "__main__":
    try:
        import pandas
    except ImportError:
        print("ERROR: pandas not found.")
        exit()
    try:
        import cachetools
    except ImportError:
        print("ERROR: cachetools not found.")
        exit()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

