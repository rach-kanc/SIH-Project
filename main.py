from flask import Flask, request, jsonify, render_template
import requests

app = Flask(__name__)

# WeatherAPI key
API_KEY = "f0320ea1882b47abadb105525250809"
BASE_URL = "http://api.weatherapi.com/v1"

# Mock weather data (for fallback)
MOCK_DATA = {
    "location": {
        "name": "DemoFarm",
        "region": "Kerala",
        "country": "India",
        "localtime": "2025-09-08 10:00"
    },
    "current": {
        "temp_c": 28,
        "temp_f": 82.4,
        "condition": {"text": "Partly Cloudy", "icon": "//cdn.weatherapi.com/weather/64x64/day/116.png"},
        "humidity": 65,
        "precip_mm": 2.0,
        "wind_kph": 10,
        "wind_dir": "NE"
    },
    "forecast": {
        "forecastday": [
            {
                "date": "2025-09-08",
                "day": {
                    "avgtemp_c": 28,
                    "condition": {"text": "Partly Cloudy", "icon": "//cdn.weatherapi.com/weather/64x64/day/116.png"},
                    "daily_chance_of_rain": 45
                }
            },
            {
                "date": "2025-09-09",
                "day": {
                    "avgtemp_c": 30,
                    "condition": {"text": "Sunny", "icon": "//cdn.weatherapi.com/weather/64x64/day/113.png"},
                    "daily_chance_of_rain": 10
                }
            },
            {
                "date": "2025-09-10",
                "day": {
                    "avgtemp_c": 26,
                    "condition": {"text": "Moderate rain", "icon": "//cdn.weatherapi.com/weather/64x64/day/302.png"},
                    "daily_chance_of_rain": 75
                }
            }
        ]
    }
}

@app.route("/")
def index():
    # Load your FarmHero HTML
    return render_template("index.html")   # make sure index.html is in templates/

@app.route("/get_weather")
def get_weather():
    location = request.args.get("q", "Delhi")  # default location
    try:
        url = f"{BASE_URL}/forecast.json?key={API_KEY}&q={location}&days=3&aqi=yes&alerts=yes"
        r = requests.get(url, timeout=5)
        r.raise_for_status()  # raise error if not 200
        data = r.json()

        # If API itself returns an error field
        if "error" in data:
            raise Exception(data["error"]["message"])
        return jsonify(data)

    except Exception as e:
        print("⚠️ Using MOCK DATA because API failed:", e)
        return jsonify(MOCK_DATA)


if __name__ == "__main__":
    app.run(debug=True)
