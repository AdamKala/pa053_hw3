from flask import Flask, request, jsonify, Response
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)

def get_airport_coordinates(iata_code):
    airport_url = f"http://www.airport-data.com/api/ap_info.php?iata={iata_code}"
    try:
        response = requests.get(airport_url)
        response.raise_for_status()
        airport_data = response.json()
        if not airport_data or not airport_data.get('latitude') or not airport_data.get('longitude'):
            return None
        return airport_data['latitude'], airport_data['longitude']
    except requests.RequestException:
        return None

def get_weather_data(latitude, longitude):
    weather_url = f"https://wttr.in/{latitude},{longitude}?format=j1"
    try:
        response = requests.get(weather_url)
        response.raise_for_status()
        weather_data = response.json()
        if 'current_condition' in weather_data and weather_data['current_condition']:
            return weather_data['current_condition'][0]['temp_C']
        else:
            return None
    except requests.RequestException:
        return None

def get_airport_temp(iata_code):
    coords = get_airport_coordinates(iata_code)
    if not coords:
        return None
    latitude, longitude = coords
    return get_weather_data(latitude, longitude)

def generate_response(result, accept_header):
    if "xml" in accept_header:
        root = ET.Element("result")
        root.text = str(result)
        xml_response = ET.tostring(root)
        return Response(xml_response, mimetype="application/xml")
    else:
        return jsonify(result)

@app.route('/', methods=['GET'])
def handle_request():
    query_airport = request.args.get('queryAirportTemp')
    query_stock = request.args.get('queryStockPrice')
    query_eval = request.args.get('queryEval')

    params_present = sum([query_airport is not None, query_stock is not None, query_eval is not None])
    if params_present != 1:
        return "Exactly one parameter must be provided", 400

    accept = request.headers.get('Accept', '')

    if query_airport:
        temp = get_airport_temp(query_airport.upper()) 
        if temp is None:
            return "Invalid airport code or weather service unavailable", 400
        return generate_response(temp, accept)


    return "Unexpected error", 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
