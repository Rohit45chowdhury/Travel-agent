
import os
import re
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

BASE_URL = "https://indian-railway-irctc.p.rapidapi.com/api/trains/v1"

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": "indian-railway-irctc.p.rapidapi.com"
}



def parse_train_query(query: str):
    query = query.lower()

    match = re.search(r'from\s+(.*?)\s+to\s+(.*?)(?:\s+on|$)', query)

    source = match.group(1).strip() if match else ""
    destination = match.group(2).strip() if match else ""

    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', query)

    if date_match:
        date = date_match.group(1)
    else:
        date = datetime.now().strftime("%Y-%m-%d")

    return source, destination, date



def get_train_status(train_number: str, date: str):
    url = f"{BASE_URL}/train/status"

    params = {
        "train_number": str(train_number),
        "departure_date": date.replace("-", ""),
        "isH5": "true",
        "client": "web",
        "deviceIdentifier": "PythonScript"
    }

    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=10)

        try:
            data = res.json()
        except:
            return {"error": True, "message": "Invalid JSON response"}

        if res.status_code == 200:
            return data

        return {"error": True, "message": f"Status Code {res.status_code}"}

    except Exception as e:
        return {"error": True, "message": str(e)}



def get_trains_from_llm(source, dest):
    return [
        {"name": "Rajdhani Express", "number": "12301"},
        {"name": "Duronto Express", "number": "12261"},
        {"name": "Garib Rath Express", "number": "12909"}
    ]



def format_train_status(train_name, train_number, status):

    
    if isinstance(status, str):
        return f""" {train_name} ({train_number})
 Unexpected response: {status}
"""

    
    if not isinstance(status, dict):
        return f""" {train_name} ({train_number})
 Invalid API response type
"""

    
    if status.get("error"):
        return f""" {train_name} ({train_number})
 {status.get('message', 'Unknown error')}
"""

    try:
        
        body = status.get("body", {})

        if not isinstance(body, dict) or not body:
            return f""" {train_name} ({train_number})
 No live status available
"""

        current_station = body.get("current_station", "Unknown")

        message = body.get("train_status_message", "No update")
        message = re.sub('<.*?>', '', message) 

        return f""" {train_name} ({train_number})
 Current Station: {current_station}
Status: {message}
"""

    except Exception as e:
        return f""" {train_name} ({train_number})
 Parsing Error: {str(e)}
"""



def train_tool(query: str):
    source_city, dest_city, date = parse_train_query(query)

    if not source_city or not dest_city:
        return " Try: from Delhi to Mumbai on 2026-03-21"

    trains_list = get_trains_from_llm(source_city, dest_city)

    results = []

    for train in trains_list:
        status = get_train_status(train["number"], date)

        formatted = format_train_status(
            train["name"],
            train["number"],
            status
        )

        results.append(formatted)

    return "\n".join(results)



if __name__ == "__main__":
    print(train_tool("from delhi to mumbai on 2026-03-21"))
