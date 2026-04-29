import os
import requests
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY") or os.getenv("HOTEL_API_KEY") 


def parse_hotel_query(query: str):
    query = query.lower()
    match = re.search(r'in\s+(.*?)(?:\s+on|\s+for|$)', query)
    city = match.group(1).strip() if match else ""

    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', query)
    date = date_match.group(1) if date_match else None

    return city, date


def get_hotels(city, checkin=None):
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "booking-com.p.rapidapi.com"
    }

    
    if not checkin:
        checkin = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    checkout = (datetime.strptime(checkin, "%Y-%m-%d") + timedelta(days=2)).strftime("%Y-%m-%d")

    try:
        
        res1 = requests.get(
            "https://booking-com.p.rapidapi.com/v1/hotels/locations",
            headers=headers,
            params={"name": city, "locale": "en-gb"},
            timeout=10
        )

        loc_data = res1.json()
        print(f"DEBUG loc_data: {loc_data[:1] if isinstance(loc_data, list) else loc_data}")  # ✅ debug

        if not isinstance(loc_data, list) or len(loc_data) == 0:
            return []

        dest_id = loc_data[0].get("dest_id")
        dest_type = loc_data[0].get("dest_type", "city")

       
        res2 = requests.get(
            "https://booking-com.p.rapidapi.com/v1/hotels/search",
            headers=headers,
            params={
                "dest_id": dest_id,
                "dest_type": dest_type,
                "checkin_date": checkin,       
                "checkout_date": checkout,      
                "adults_number": 2,
                "room_number": 1,
                "order_by": "popularity",
                "locale": "en-gb",
                "currency": "INR",
                "filter_by_currency": "INR",
                "units": "metric"
            },
            timeout=10
        )

        data = res2.json()
        print(f"DEBUG hotel count: {len(data.get('result', []))}") 

        hotels = []
        for item in data.get("result", [])[:5]:
            hotels.append({
                "name": item.get("hotel_name", "N/A"),
                "rating": item.get("review_score", "N/A"),
                "address": item.get("address", "N/A"),
                "price": item.get("min_total_price", "N/A")
            })

        return hotels

    except Exception as e:
        print(f"DEBUG Hotel API Error: {e}")  
        return {"error": True, "message": str(e)}


def format_hotel(hotel):
    return f"""🏨 {hotel['name']}
📍 Address: {hotel['address']}
⭐ Rating: {hotel['rating']}
💰 Price: ₹{hotel['price']}
"""


def hotel_tool(query: str):
    city, date = parse_hotel_query(query)

    if not city:
        return "🏨 Try: hotels in Delhi on 2026-05-10"

    hotels = get_hotels(city, checkin=date)

    if isinstance(hotels, dict) and hotels.get("error"):
        return f"❌ API Error: {hotels['message']}"

    if not hotels:
        return f"❌ No hotels found in {city.title()}"

    results = [f"🏨 **Hotels in {city.title()}**\n"]
    for hotel in hotels:
        results.append(format_hotel(hotel))

    return "\n".join(results)


if __name__ == "__main__":
    print(hotel_tool("hotels in Goa"))