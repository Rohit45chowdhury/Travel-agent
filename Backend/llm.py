import os
import re
from dotenv import load_dotenv
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from datetime import datetime

from Backend.gemini import gemini
from Backend.train import train_tool
from Backend.hotel import hotel_tool
from Backend.map import get_route_data
from Backend.flight import (
    get_iata_code,
    create_offer_request,
    get_offers
)

load_dotenv()


# STATE
class TravelState(TypedDict):
    query: str
    intent: str
    output: str
    route_data: dict



# GENERAL CHAT

def handle_general(state: TravelState):
    try:
        prompt = f"""
You are a smart AI travel assistant.

Rules:
- Be friendly and helpful
- Answer travel questions clearly
- Give practical advice
- Keep response under 5 lines

User: {state['query']}
"""
        response = gemini(prompt)
        return {**state, "output": response}

    except Exception as e:
        return {**state, "output": f"Error: {str(e)}"}



# INTENT DETECTION

def detect_intent(state: TravelState):
    query = state["query"].lower()

    train_keywords = ["train", "rail", "railway", "irctc"]
    flight_keywords = ["flight", "fly", "air", "plane", "ticket"]
    hotel_keywords = ["hotel", "stay", "room", "booking", "resort"]
    trip_keywords = ["trip", "travel", "plan", "itinerary", "vacation", "holiday"]
    map_keywords = ["route", "map", "direction", "distance", "how to go"]
    small_talk = ["hi", "hello", "hey", "how are you"]
    general_keywords = [
        "best time", "visit", "when to", "what to", "how to",
        "tips", "weather", "temperature", "season", "culture",
        "food", "visa", "carry", "safe", "budget", "cost",
        "why", "which", "should i", "recommend", "suggest",
        "famous", "popular", "attraction", "place", "tourist"
    ]

    if any(word in query for word in hotel_keywords):
        intent = "hotel"

    elif any(word in query for word in flight_keywords):
        intent = "flight"

    elif any(word in query for word in train_keywords):
        intent = "train"

    
    elif any(word in query for word in general_keywords):
        intent = "general"

    elif any(word in query for word in small_talk):
        intent = "general"

    elif any(word in query for word in map_keywords) and " to " in query:
        intent = "map"

   
    elif " to " in query and len(query.split()) <= 5:
        intent = "map"

    elif any(word in query for word in trip_keywords):
        intent = "trip"

    else:
        intent = "general"  

    print(f"DEBUG INTENT → '{query}' = {intent}")  

    return {**state, "intent": intent}

# TRAIN 

def handle_train(state: TravelState):
    try:
        raw = train_tool(state["query"])

        if not raw:
            return {**state, "output": " No trains found"}

        result = "Train Results\n\n"

        
        for i, train in enumerate(raw[:5], 1):
            name = train.get("name", "N/A")
            number = train.get("number", "")
            depart = train.get("departure", "N/A")
            arrive = train.get("arrival", "N/A")
            classes = ", ".join(train.get("classes", [])) if train.get("classes") else "N/A"

            result += f"""
 Option {i}

 {name} {f"({number})" if number else ""}

 {depart} → {arrive}

 Classes: {classes}

"""

        result += " Want seat availability or booking help?"

        return {**state, "output": result}

    except Exception as e:
        return {**state, "output": f" Train Error: {str(e)}"}


# FLIGHT 

def handle_flight(state: TravelState):
    query = state["query"].lower()

    try:
       
        match = re.search(
            r'(?:show\s+)?(?:flights?\s+)?(?:fly\s+)?(?:from\s+)?([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+?)(?:\s+on\s+(\d{4}-\d{2}-\d{2}))?$',
            query.strip()
        )

        if not match:
            return {
                **state,
                "output": " Try like: flight from Delhi to Mumbai on 2026-04-10"
            }

        origin_city = re.sub(r'\b(show|flights?|fly|from|air|plane|ticket)\b', '', match.group(1)).strip()
        destination_city = re.sub(r'\b(show|flights?|fly|to)\b', '', match.group(2)).strip()
        departure_date = match.group(3) if match.group(3) else datetime.today().strftime("%Y-%m-%d")


        today = datetime.today()
        dep_date = datetime.strptime(departure_date, "%Y-%m-%d")

        if (dep_date - today).days > 330:
            return {
                **state,
                "output": f"""
 Flights: {origin_city.title()} → {destination_city.title()}

 {departure_date} is too far in advance.
Bookings usually open ~11 months before departure.

 Try a nearer date.
"""
            }


        origin = get_iata_code(origin_city)
        destination = get_iata_code(destination_city)

        if not origin or not destination:
            return {**state, "output": " Invalid city names"}

        
        # API DATA
        
        data = {
            "journey_type": "oneway",
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": None,
            "passengers": 1,
            "cabin": "economy"
        }

        offer_req = create_offer_request(data)
        offers = get_offers(offer_req["id"])

        if not offers:
            return {**state, "output": " No flights found"}

        offers = sorted(offers, key=lambda x: float(x["total_amount"]))


        result = f" Flights: {origin_city.title()} → {destination_city.title()}"

        for i, offer in enumerate(offers[:3], 1):
            seg = offer["slices"][0]["segments"][0]

            result += f"""
             Option {i}
             {offer['total_amount']} {offer['total_currency']}
             {seg['origin']['iata_code']} → {seg['destination']['iata_code']}
             {seg['departing_at'][:16]} → {seg['arriving_at'][:16]}
             {seg['operating_carrier']['name']}
            """

        

        return {**state, "output": result}

    except Exception as e:
        return {**state, "output": f" Flight Error: {str(e)}"}


# HOTEL 

import re

def handle_hotel(state: TravelState):
    try:
        query = state["query"]

        match = re.search(r'(?:hotels?\s+in|stay\s+in|rooms?\s+in)\s+(.+)', query.lower())
        city = match.group(1).strip().title() if match else query

        print(f"city: {city}")

        raw = hotel_tool(state["query"])

        if not raw:
            return {**state, "output": " No hotels found for your query"}


        if isinstance(raw, dict):
            raw = raw.get("hotels", [])

        if not isinstance(raw, list):
            return {**state, "output": " Invalid hotel data format"}


        def parse_price(price):
            if isinstance(price, (int, float)):
                return price
            if isinstance(price, str):
                return int(re.sub(r"[^\d]", "", price) or 0)
            return 0

        is_budget = "budget" in query
        is_luxury = "luxury" in query


        result = " **Hotel Results**\n"
        result += "=" * 35 + "\n\n"

        hotels_found = 0

        for i, hotel in enumerate(raw):
            if hotels_found >= 5:
                break

            name = hotel.get("name", "N/A")
            price = hotel.get("price", "N/A")
            rating = hotel.get("rating", "N/A")
            location = hotel.get("location", "N/A")

            clean_price = parse_price(price)


            if is_budget and clean_price > 3000:
                continue
            if is_luxury and clean_price and clean_price < 5000:
                continue

            hotels_found += 1


            result += f"""
 Option {hotels_found}

 Name: {name}
 Location: {location}
 Price: {price}
 Rating: {rating}

-----------------------------------
"""


        if hotels_found == 0:
            return {
                **state,
                "output": " No hotels match your preference. Try removing filters."
            }


        result += "\n Try: budget hotels / luxury hotels / near airport"

        return {
            **state,
            "output": result.strip()
        }

    except Exception as e:
        return {
            **state,
            "output": f" Hotel Error: {str(e)}"
        }



# TRIP 

def handle_trip(state: TravelState):
    query = state["query"]

    try:
        prompt = f"""
You are an expert travel planner AI.

Your task is to generate a HIGH QUALITY, PRACTICAL travel plan.

IMPORTANT RULES:
- Be realistic with budget and duration
- Keep itinerary logical (no random jumps)
- Use simple, clean formatting
- Do NOT add extra commentary
- Avoid long paragraphs

FORMAT (STRICT):

 Destination: <place>

 Duration: <X days>

 Budget: <approx INR amount>

 Itinerary:
Day 1: <plan>
Day 2: <plan>
Day 3: <plan>
(extend if needed)

 Food:
- <local food 1>
- <local food 2>
- <local food 3>

 Travel Tips:
- <tip 1>
- <tip 2>
- <tip 3>

 Packing Tips:
- <item 1>
- <item 2>

User Query: {query}
"""

        plan = gemini(prompt)

        if not plan or len(plan.strip()) < 20:
            plan = " Could not generate a proper travel plan. Please try again."

        return {
            **state,
            "output": f" **Travel Plan**\n\n{plan.strip()}"
        }

    except Exception as e:
        return {
            **state,
            "output": f" Trip Error: {str(e)}"
        }



# MAP

def handle_map(state: TravelState):
    try:
        query = state["query"].lower()


        match = re.search(r'(?:from\s+)?(.+?)\s+to\s+(.+)', query)

        if match:
            start = match.group(1).replace("show route", "").replace("route", "").strip()
            end = match.group(2).strip()
            clean_query = f"{start} to {end}"
        else:
            clean_query = query


        route = get_route_data(clean_query)

        if not route:
            return {
                **state,
                "output": " Route not found. Try: Kolkata to Haldia"
            }

        start = route['start'].title()
        end = route['end'].title()

        distance = route['segment']['distance'] / 1000
        duration = route['segment']['duration'] / 60

   
        result = f"""
 Route: {start} → {end}

 Distance: {round(distance, 2)} km  
 Duration: {round(duration, 2)} mins
"""

        return {
            **state,
            "output": result,
            "route_data": route
        }

    except Exception as e:
        return {
            **state,
            "output": f" Map Error: {str(e)}"
        }


# ROUTER

def router(state: TravelState):
    return state["intent"]


def final_output(state: TravelState):
    return dict(state)



# GRAPH

builder = StateGraph(TravelState)

builder.add_node("intent", detect_intent)
builder.add_node("train", handle_train)
builder.add_node("flight", handle_flight)
builder.add_node("trip", handle_trip)
builder.add_node("hotel", handle_hotel)
builder.add_node("map", handle_map)
builder.add_node("general", handle_general)
builder.add_node("output", final_output)

builder.add_edge(START, "intent")

builder.add_conditional_edges(
    "intent",
    router,
    {
        "train": "train",
        "flight": "flight",
        "hotel": "hotel",
        "trip": "trip",
        "map": "map",
        "general": "general"
    }
)

builder.add_edge("train", "output")
builder.add_edge("flight", "output")
builder.add_edge("trip", "output")
builder.add_edge("hotel", "output")
builder.add_edge("map", "output")
builder.add_edge("general", "output")
builder.add_edge("output", END)

graph = builder.compile()



# MAIN

def travel_agent(query: str):
    return graph.invoke({
        "query": query,
        "intent": "",
        "output": "",
        "route_data": None
    })


# CLI

if __name__ == "__main__":
    print(" AI Travel Agent Started\n")

    while True:
        q = input(" Enter query: ")
        if q.lower() in ["exit", "quit"]:
            break

        result = travel_agent(q)
        print("\n" + result["output"])