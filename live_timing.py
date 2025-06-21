from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from datetime import datetime, timedelta, timezone
import threading
import time

CORS(app)
app = Flask(__name__)
OPENF1_BASE = "https://api.openf1.org/v1"

# Initialize global variables to hold the latest live session data
live_session_data = {}
team_radio_data = {}
race_control_data = {}

# Function to fetch sessions data
def fetch_sessions(date=None):
    try:
        url = f"{OPENF1_BASE}/sessions"
        params = {"date": date} if date else {}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("Error fetching sessions:", e)
        return []

# Function to get the session key by filter
def get_session_key_by_filter(session_filter=None):
    now_utc = datetime.now(timezone.utc)
    dates_to_check = [
        (now_utc - timedelta(days=1)).date().isoformat(),
        now_utc.date().isoformat(),
        (now_utc + timedelta(days=1)).date().isoformat()
    ]

    sessions = []
    for date in dates_to_check:
        sessions += fetch_sessions(date)

    if not sessions:
        sessions = fetch_sessions()

    sessions = sorted(sessions, key=lambda s: s.get("session_start_utc", ""), reverse=True)

    for session in sessions:
        start_str = session.get("session_start_utc")
        if not start_str:
            continue
        try:
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            if session_filter:
                if session.get("session_name", "").lower() != session_filter.lower():
                    continue
            if now_utc >= start_dt - timedelta(minutes=10):
                return session["session_key"]
        except Exception:
            continue

    if sessions:
        return sessions[0].get("session_key")
    return None

# Function to fetch live position data
def fetch_live_data(session_key):
    try:
        response = requests.get(
            f"{OPENF1_BASE}/position",
            params={"session_key": session_key},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("Error fetching live data:", e)
        return []

# Function to fetch team radio data
def fetch_team_radio(session_key):
    try:
        response = requests.get(
            f"{OPENF1_BASE}/team_radio",
            params={"session_key": session_key},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("Error fetching team radio:", e)
        return []

# Function to fetch Race Control data
def fetch_race_control(session_key):
    try:
        response = requests.get(
            f"{OPENF1_BASE}/race_control",
            params={"session_key": session_key},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("Error fetching race control data:", e)
        return []

# Background thread to fetch all live data periodically
def fetch_live_data_periodically():
    global live_session_data, team_radio_data, race_control_data
    while True:
        session_key = get_session_key_by_filter()
        if session_key:
            # Fetch position data
            raw_data = fetch_live_data(session_key)
            if raw_data:
                latest_data = {}
                for entry in raw_data:
                    number = entry.get("driver_number")
                    if not number:
                        continue
                    if number not in latest_data or (entry.get("utc") or "") > (latest_data[number].get("utc") or ""):
                        latest_data[number] = entry
                sorted_drivers = sorted(latest_data.values(), key=lambda x: x.get("position", 999))
                live_session_data = [
                    {
                        "Driver Number": driver.get("driver_number"),
                        "Code": driver.get("driver_code"),
                        "Gap to Car Ahead": driver.get("gap_to_car_ahead", "N/A"),
                        "Laps Completed": driver.get("laps_completed", 0),
                        "Position": driver.get("position", "N/A"),
                        "Lap Indicator": f"L{driver.get('laps_completed', 0)}" if driver.get('laps_completed', 0) else "Out"
                    }
                    for driver in sorted_drivers
                ]

            # Fetch team radio
            team_radio_data = [
                {
                    "Driver": msg.get("driver"),
                    "Radio Message": msg.get("radio_message")
                }
                for msg in fetch_team_radio(session_key)
            ]

            # Fetch race control messages
            race_data = fetch_race_control(session_key)
            if race_data:
                sorted_msgs = sorted(race_data, key=lambda x: x.get("utc", ""), reverse=True)
                race_control_data["messages"] = [
                    {
                        "Category": msg.get("category"),
                        "Message": msg.get("message"),
                        "Time UTC": msg.get("utc")
                    }
                    for msg in sorted_msgs[:10]
                ]
        time.sleep(5)

# Start background task
def start_background_task():
    thread = threading.Thread(target=fetch_live_data_periodically)
    thread.daemon = True
    thread.start()

start_background_task()

@app.route("/")
def home():
    return "F1 Live Timing API – Visit /live_session_data or /live_session_data/<SessionName>"

@app.route("/live_session_data", defaults={'session_filter': None, 'driver_filter': None})
@app.route("/live_session_data/<session_filter>", defaults={'driver_filter': None})
@app.route("/live_session_data/<session_filter>/<driver_filter>")
def live_session_data_route(session_filter, driver_filter):
    if not live_session_data:
        return jsonify({
            "session": session_filter or "Unknown",
            "drivers": [],
            "team_radio": [],
            "race_control": [],
            "message": f"No live data currently available for session '{session_filter or 'N/A'}'. Please check back when the session is live."
        })

    filtered_live_data = [
        data for data in live_session_data if driver_filter is None or (data['Code'] and data['Code'].lower() == driver_filter.lower())
    ]
    filtered_radio_data = [
        msg for msg in team_radio_data if driver_filter is None or (msg['Driver'] and msg['Driver'].lower() == driver_filter.lower())
    ]

    return jsonify({
        "session": session_filter or "All",
        "drivers": filtered_live_data,
        "team_radio": filtered_radio_data,
        "race_control": race_control_data.get("messages", [])
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

