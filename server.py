from fetch_property_data import get_properties_transit_info
from fetch_property_data import get_properties_nearby_transit_locations
from fetch_property_data import get_properties_transit_info_and_locations
from flask import Flask, request
import json


app = Flask(__name__)

@app.route('/transit', methods=['POST'])
def get_transit_info():
    request_data = request.get_json()
    if ('with_locations' in request_data) and request_data['with_locations']:
        result = get_properties_transit_info_and_locations(request_data)
    else:
        result = get_properties_transit_info(request_data)
    return json.dumps(result)

@app.route('/locations', methods=['POST'])
def get_transit_locations():
    request_data = request.get_json()
    result = get_properties_nearby_transit_locations(request_data)
    return json.dumps(result)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')