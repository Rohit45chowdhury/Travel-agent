import folium
from streamlit_folium import st_folium
import openrouteservice
import re
import os
from dotenv import load_dotenv

load_dotenv()

# API client
client = openrouteservice.Client(key=os.getenv("MAP_API_KEY"))


#  CACHE

CACHE = {
    "kolkata": (88.3639, 22.5726),
    "haldia": (88.0698, 22.0667),
    "delhi": (77.1025, 28.7041),
    "mumbai": (72.8777, 19.0760),
    "manali": (77.1892, 32.2432),
    "goa": (74.1240, 15.2993),
}


#  GET COORDS

def get_coords(place):
    place = place.lower().strip()

    if place in CACHE:
        return CACHE[place]

    try:
        res = client.pelias_search(text=place)
        if res and res.get("features"):
            coords = res["features"][0]["geometry"]["coordinates"]
            CACHE[place] = tuple(coords)
            return tuple(coords)
    except:
        return None

    return None



#  GET ROUTE DATA

def get_route_data(query):

    match = re.search(r'(.*?)\s+to\s+(.*)', query.lower())

    if not match:
        return None

    start = match.group(1).strip()
    end = match.group(2).strip()

    start_coords = get_coords(start)
    end_coords = get_coords(end)

    if not start_coords or not end_coords:
        return None

    try:
        route = client.directions(
            coordinates=[start_coords, end_coords],
            profile='driving-car',
            format='geojson'
        )

        geometry = route['features'][0]['geometry']
        segment = route['features'][0]['properties']['segments'][0]

        return {
            "start": start,
            "end": end,
            "start_coords": start_coords,
            "end_coords": end_coords,
            "geometry": geometry,
            "segment": segment
        }

    except:
        return None



#  SHOW MAP

def show_map(route_data, st):

    if not route_data:
        return

    data = route_data

    distance = data['segment']['distance'] / 1000
    duration = data['segment']['duration'] / 60

    st.subheader("🗺 Route Map")
    st.success(f"{data['start'].title()} → {data['end'].title()}")
    st.info(f"📏 {round(distance, 2)} km | ⏱ {round(duration, 2)} min")

    m = folium.Map(
        location=[data["start_coords"][1], data["start_coords"][0]],
        zoom_start=7
    )

    # Start
    folium.Marker(
        [data["start_coords"][1], data["start_coords"][0]],
        icon=folium.Icon(color="green")
    ).add_to(m)

    # End
    folium.Marker(
        [data["end_coords"][1], data["end_coords"][0]],
        icon=folium.Icon(color="red")
    ).add_to(m)

    # Route
    folium.GeoJson(
        data["geometry"],
        style_function=lambda x: {"color": "blue", "weight": 5}
    ).add_to(m)

    st_folium(m, width=500, height=350)