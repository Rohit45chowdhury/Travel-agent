import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("DUFFEL_API_KEY")
if not API_KEY:
    raise ValueError(" DUFFEL_API_KEY missing!")

BASE_URL = "https://api.duffel.com"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Duffel-Version": "v2",
}

# CITY  IATA
CITY_TO_IATA = {
    "delhi": "DEL", "new delhi": "DEL",
    "mumbai": "BOM", "bombay": "BOM",
    "bangalore": "BLR", "bengaluru": "BLR",
    "goa": "GOI",
    "hyderabad": "HYD",
    "chennai": "MAA", "madras": "MAA",
    "kolkata": "CCU", "calcutta": "CCU",
    "pune": "PNQ",
    "ahmedabad": "AMD",
    "jaipur": "JAI",
    "lucknow": "LKO",
    "kochi": "COK", "cochin": "COK",
}

def get_iata_code(city):
    city = city.lower().strip()
    if city in CITY_TO_IATA:
        return CITY_TO_IATA[city]

    try:
        res = requests.get(
            f"{BASE_URL}/places/suggestions",
            headers=HEADERS,
            params={"query": city},
            timeout=10
        )
        res.raise_for_status()
        data = res.json().get("data", [])
        for place in data:
            if place.get("type") == "airport" and place.get("iata_code"):
                return place["iata_code"]
    except Exception as e:
        print(f" IATA API Error: {e}")

    return None

def get_user_input():
    print("\n Flight Search\n")
    journey_type = input("Journey Type (oneway/roundtrip): ").strip().lower()
    origin_city = input("From (city): ").strip()
    destination_city = input("To (city): ").strip()
    departure_date = input("Departure Date (YYYY-MM-DD): ").strip()
    return_date = None
    if journey_type == "roundtrip":
        return_date = input("Return Date (YYYY-MM-DD): ").strip()
    passengers = int(input("Number of passengers: ").strip())
    cabin = input("Class (economy/business/first): ").strip().lower()
    if cabin not in ["economy", "business", "first"]:
        cabin = "economy"
    origin = get_iata_code(origin_city)
    destination = get_iata_code(destination_city)
    return {
        "journey_type": journey_type,
        "origin": origin,
        "destination": destination,
        "departure_date": departure_date,
        "return_date": return_date,
        "passengers": passengers,
        "cabin": cabin
    }

CURRENCY_API_URL = "https://open.er-api.com/v6/latest"

def convert_currency(amount, from_currency, to_currency="INR"):
    try:
        url = f"{CURRENCY_API_URL}/{from_currency}"
        res = requests.get(url, timeout=10)
        data = res.json()
        rate = data.get("rates", {}).get(to_currency)
        if rate:
            return amount * rate
    except Exception as e:
        print(f" Currency API Error: {e}")
    return amount

def create_offer_request(data):
    try:
        slices = [{
            "origin": data["origin"],
            "destination": data["destination"],
            "departure_date": data["departure_date"]
        }]
        if data["journey_type"] == "roundtrip" and data["return_date"]:
            slices.append({
                "origin": data["destination"],
                "destination": data["origin"],
                "departure_date": data["return_date"]
            })
        payload = {
            "data": {
                "slices": slices,
                "passengers": [{"type": "adult"} for _ in range(data["passengers"])],
                "cabin_class": data["cabin"]
            }
        }
        res = requests.post(f"{BASE_URL}/air/offer_requests", headers=HEADERS, json=payload, timeout=40)
        res.raise_for_status()
        return res.json().get("data")
    except Exception as e:
        print(f" Offer Request Error: {e}")
        return None

def get_offers(request_id):
    try:
        res = requests.get(
            f"{BASE_URL}/air/offers",
            headers=HEADERS,
            params={"offer_request_id": request_id, "max_connections": 0, "sort": "total_amount"},
            timeout=40
        )
        res.raise_for_status()
        return res.json().get("data", [])
    except Exception as e:
        print(f" Offers Error: {e}")
        return []

def display_offers(offers):
    if not offers:
        print(" No flights found")
        return
    print("\n" + "="*50)
    print(" TOP FLIGHTS")
    print("="*50)
    for i, offer in enumerate(offers[:5], 1):
        try:
            segment = offer["slices"][0]["segments"][0]
            price = float(offer.get("total_amount", 0))
            currency = offer.get("total_currency", "USD")
            inr_price = convert_currency(price, currency)
            print(f"\n Option {i}")
            print(f" ₹{round(inr_price)} INR ({price} {currency})")
            print(f" {segment['origin']['iata_code']} → {segment['destination']['iata_code']}")
            print(f" {segment['departing_at'][:16]} → {segment['arriving_at'][:16]}")
            print(f" {segment['operating_carrier']['name']}")
        except Exception:
            print(f" Skipping corrupted offer {i}")



# flight book
def get_passenger_details(num_passengers):
    passengers = []
    for i in range(num_passengers):
        print(f"\n Passenger {i+1} Details:")

        title = input("  Title (mr/ms/mrs): ").strip().lower()
        given_name = input("  First Name: ").strip()
        family_name = input("  Last Name: ").strip()

        dob = input("  DOB (YYYY-MM-DD): ").strip()
        if len(dob.split("-")[0]) == 2:
            parts = dob.split("-")
            dob = f"{parts[2]}-{parts[1]}-{parts[0]}"

        email = input("  Email: ").strip()

        phone = input("  Phone: ").strip()
        if not phone.startswith("+"):
            phone = "+91" + phone

        gender = input("  Gender (m/f): ").strip().lower()

        passengers.append({
            "type": "adult",
            "title": title,          
            "given_name": given_name,
            "family_name": family_name,
            "born_on": dob,
            "email": email,
            "phone_number": phone,
            "gender": gender,
        })
    return passengers

def book_flight(offer_id, passengers_info, amount, currency):
    try:
        
        offer_res = requests.get(f"{BASE_URL}/air/offers/{offer_id}", headers=HEADERS, timeout=20)
        offer_data = offer_res.json().get("data", {})
        offer_passengers = offer_data.get("passengers", [])

        
        for i, p in enumerate(passengers_info):
            if i < len(offer_passengers):
                p["id"] = offer_passengers[i]["id"]

        payload = {
            "data": {
                "selected_offers": [offer_id],
                "passengers": passengers_info,
                "payments": [{
                    "type": "balance",
                    "amount": str(amount),
                    "currency": currency
                }]
            }
        }
        res = requests.post(f"{BASE_URL}/air/orders", headers=HEADERS, json=payload, timeout=40)
        
        
        if not res.ok:
            print(f" API Response: {res.json()}")
            res.raise_for_status()
            
        return res.json().get("data")
    except Exception as e:
        print(f" Booking Error: {e}")
        return None

if __name__ == "__main__":
    print(" Flight Booking System")
    user_data = get_user_input()

    if not user_data["origin"] or not user_data["destination"]:
        print(" Invalid cities")
        exit()

    print("\n Searching Flights...\n")
    offer_req = create_offer_request(user_data)

    if offer_req:
        offers = get_offers(offer_req["id"])
        display_offers(offers)

        if offers:
            try:
                choice = int(input("\n Kaun sa option book karna hai? (1-5): ").strip()) - 1
                selected_offer = offers[choice]
            except (ValueError, IndexError):
                print(" Invalid choice")
                exit()

            confirm = input(f"\n Confirm booking? (yes/no): ").strip().lower()
            if confirm != "yes":
                print(" Booking cancelled")
                exit()

            passengers_info = get_passenger_details(user_data["passengers"])

            print("\n Booking...")
            order = book_flight(
                offer_id=selected_offer["id"],
                passengers_info=passengers_info,
                amount=selected_offer["total_amount"],
                currency=selected_offer["total_currency"]
            )

            if order:
                print(f"\n Booking Confirmed!")
                print(f" Booking Ref: {order.get('booking_reference')}")
            else:
                print(" Booking failed")