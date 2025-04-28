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

def get_stock_price(stock_symbol):
    stock_api_url = f"https://finnhub.io/api/v1/quote?symbol={stock_symbol}&token=d07nm1pr01qp8st5agv0d07nm1pr01qp8st5agvg"
    try:
        response = requests.get(stock_api_url)
        response.raise_for_status()
        stock_data = response.json()
        if 'c' in stock_data: 
            return stock_data['c']
        else:
            return None
    except requests.RequestException:
        return None

def generate_response(result, accept_header):
    if "xml" in accept_header:
        root = ET.Element("result")
        root.text = str(result)
        xml_response = ET.tostring(root)
        return Response(xml_response, mimetype="application/xml")
    else:
        return jsonify(result)

def evaluate_expression(expr):
    import re

    tokens = re.findall(r'\d+|\+|\-|\*|\/|\(|\)', expr.replace(' ', ''))
    tokens.append('EOF') 

    def parse_expression(index):
        value, index = parse_term(index)
        while tokens[index] in ('+', '-'):
            op = tokens[index]
            index += 1
            next_value, index = parse_term(index)
            if op == '+':
                value += next_value
            else:
                value -= next_value
        return value, index

    def parse_term(index):
        value, index = parse_factor(index)
        while tokens[index] in ('*', '/'):
            op = tokens[index]
            index += 1
            next_value, index = parse_factor(index)
            if op == '*':
                value *= next_value
            else:
                if next_value == 0:
                    raise ZeroDivisionError("Division by zero")
                value /= next_value
        return value, index

    def parse_factor(index):
        token = tokens[index]
        if token == '(':
            index += 1
            value, index = parse_expression(index)
            if tokens[index] != ')':
                raise ValueError("Mismatched parentheses")
            index += 1
            return value, index
        elif re.match(r'\d+', token):
            index += 1
            return int(token), index
        else:
            raise ValueError(f"Unexpected token: {token}")

    try:
        result, index = parse_expression(0)
        if tokens[index] != 'EOF':
            raise ValueError("Unexpected input after expression")
        return result
    except (IndexError, ValueError, ZeroDivisionError):
        return None


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

    if query_stock:
        stock_price = get_stock_price(query_stock.upper())
        if stock_price is None:
            return "Invalid stock symbol or stock service unavailable", 400
        return generate_response(stock_price, accept)
    
    if query_eval:
        result = evaluate_expression(query_eval)
        if result is None:
            return "Invalid expression", 400
        return generate_response(result, accept)

    return "Unexpected error", 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
