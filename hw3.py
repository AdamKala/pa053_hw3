from flask import Flask, request, jsonify, Response
import requests
import xml.etree.ElementTree as ET
import yfinance as yf
import urllib.parse

app = Flask(__name__)

OPENWEATHERMAP_API_KEY = "218c58388976602f204098c909b44744"

AIRPORT_COORDS = {
    'JFK': (40.6413, -73.7781),  # New York
    'LHR': (51.4700, -0.4543),   # London Heathrow
    'CDG': (49.0097, 2.5479),    # Paris Charles de Gaulle
    'DXB': (25.2532, 55.3657),   # Dubai
    'HND': (35.5494, 139.7798),  # Tokyo Haneda
}

def get_airport_temp(iata_code):
    coords = AIRPORT_COORDS.get(iata_code.upper())
    if not coords:
        return None
    lat, lon = coords
    try:
        weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={OPENWEATHERMAP_API_KEY}"
        response = requests.get(weather_url, timeout=5)
        response.raise_for_status() 
        data = response.json()
        return data['main']['temp']
    except Exception as e:
        print("Weather API error:", e)
        return None

def get_stock_price(symbol):
    stock = yf.Ticker(symbol.upper())
    hist = stock.history(period="1d")
    if hist.empty:
        return None
    return round(hist['Close'][0], 2)


def eval_expression(expr):
    try:
        expr = urllib.parse.unquote(expr) 
        result = eval(expr, {"__builtins__": None}, {})
        return result
    except Exception as e:
        print("Eval error:", e)
        return None

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
        temp = get_airport_temp(query_airport)
        if temp is None:
            return "Invalid airport code or weather service unavailable", 400
        return generate_response(temp, accept)

    if query_stock:
        price = get_stock_price(query_stock)
        if price is None:
            return "Invalid stock symbol", 400
        return generate_response(price, accept)

    if query_eval:
        result = eval_expression(query_eval)
        if result is None:
            return "Invalid expression", 400
        return generate_response(result, accept)

    return "Unexpected error", 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
