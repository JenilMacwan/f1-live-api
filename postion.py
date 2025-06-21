from flask import Flask, jsonify
import requests
from flask_cors import CORS
CORS(app)

app = Flask(__name__)

# Replace with actual API URL for car positions
OPENF1_POSITION_URL = "https://api.openf1.org/v1/position"

@app.route('/position.json')
def get_car_position():
    try:
        # Send GET request to fetch car positions
        response = requests.get(OPENF1_POSITION_URL)
        
        if response.status_code == 200:
            # Parse response JSON
            car_positions = response.json()
            
            # Process car positions (adjust based on API structure)
            positions = [
                {"car_number": car["car_number"], "x": car["x"], "y": car["y"]}
                for car in car_positions["cars"]
            ]
            
            return jsonify(positions)  # Return as JSON
            
        else:
            return jsonify({"error": "No session is live"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

