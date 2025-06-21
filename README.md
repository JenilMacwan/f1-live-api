# 🏎️ F1 Live Timing & Race Info API

A Flask-based API service for providing real-time Formula 1 data, including:

- 🟥 Live session timing (position, lap, gap)
- 📡 Team radio & race control updates
- 🏁 Upcoming race schedule & countdowns
- 🧑‍🔧 Driver and constructor standings
- 🌤️ Real-time circuit weather
- 🗺️ Live car positions on track

---

## 🚀 Features

### `/f1info.json` (from `server.py`)
Returns upcoming race info including:
- Next session (FP1, Quali, Race) & countdown
- Circuit, weather, flags
- Current top 3 drivers and constructors
- Last race winner
- Full 2025 calendar

### `/position.json` (from `postion.py`)
Returns real-time `x, y` car coordinates using OpenF1 API.
- Only works when session is live
- Returns: `car_number`, `x`, `y`

### `/live_session_data` (from `live_timing.py`)
Returns live driver timing and team radio:
- Driver Code, Gap, Position, Laps
- Team radio messages (if available)
- Race control messages

Supports:
```
/live_session_data              – All live data
/live_session_data/qualifying  – Specific session (e.g., race, sprint)
/live_session_data/race/VER    – Filter by driver code
```

---

## 📦 Requirements

Create `requirements.txt`:

```txt
Flask
fastf1
requests
cachetools
beautifulsoup4
selenium
babel
flask-cors
```

Install with:

```bash
pip install -r requirements.txt
```

Also, install a Selenium-compatible driver (e.g., ChromeDriver) if scraping is enabled.

---

## 🔧 How to Run

### 1. Start the F1 Info Server:
```bash
python server.py
```

### 2. Start Live Timing Server:
```bash
python live_timing.py
```

### 3. Start Car Position Server:
```bash
python postion.py
```

Access API in browser or via `curl`:
```bash
curl http://localhost:5000/f1info.json
```

---

## 🌐 APIs Used

- [OpenF1 API](https://openf1.org/)
- [Jolpica API](https://api.jolpi.ca/)
- [FastF1](https://theoehrly.github.io/Fast-F1/)
- [Open-Meteo](https://open-meteo.com/)

---

## 📌 Notes

- Auto-refresh every 5 seconds for live timing
- Driver nationalities and circuit flags are hardcoded for consistency
- Circuit coordinates fallback if not in API
- You Need To Host It Locally
---

## 📸 Example JSON Response

`GET /f1info.json`:

```json
{
  "Race": {
    "Name": "Spanish GP",
    "Circuit-Name": "Circuit de Barcelona-Catalunya",
    "Location": "Barcelona",
    "Country": "🇪🇸",
    "Weather": "☀️ 27°C",
    "CountdownToNextSession": "⏱️ Quali in 1d 2h 13m",
    "CountdownToRace": "🟩 Race in 2d 6h 15m",
    "NextSession": "Quali"
  },
  ...
}
```

---

## 🤝 Contribution

Pull requests and ideas are welcome! Please open an issue for discussion before starting.

---

## 📜 License

MIT License
