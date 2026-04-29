import sys
import os
import streamlit as st
import uuid
from dotenv import load_dotenv
import time

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from Backend.db import (
    init_db, save_message, load_messages, clear_chat,
    get_all_sessions, init_memory, save_memory, load_memory
)
from Backend.llm import gemini, handle_flight, train_tool, hotel_tool, handle_map, travel_agent
from Backend.map import show_map

init_db()
init_memory()
load_dotenv()

st.set_page_config(
    page_title="AI Travel Agent",
    page_icon="✈️",
    layout="wide"
)


st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

USER_ID = st.session_state.get("user", "default_user")

# Session init
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "map_message_index" not in st.session_state:
    st.session_state.map_message_index = None

if "messages" not in st.session_state:
    raw = load_messages(st.session_state.session_id)
    st.session_state.messages = [
        {"role": str(m.get("role", "user")), "content": str(m.get("content", ""))}
        for m in raw if isinstance(m, dict)
    ]

if "route_data" not in st.session_state:
    st.session_state.route_data = None


# Memory extract
def extract_memory(user_input):
    prompt = f"""Extract long-term memory from this message.
Rules:
- Only store important user info (name, preference, location, interests)
- Ignore temporary info
- Return ONLY one short sentence
- If nothing important, return: NONE

Message: {user_input}"""
    try:
        result = gemini(prompt)
        if result and "NONE" not in result.upper() and len(result.strip()) > 5:
            return result.strip()
    except:
        pass
    return None



with st.sidebar:
    st.title("✈️ Travel Agent")
    st.divider()

    
    if not st.session_state.get("logged_in"):
        st.markdown("#### 👤 Account")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔐 Login", use_container_width=True):
                st.switch_page("pages/security.py")
        with col_b:
            if st.button("📝 Signup", use_container_width=True):
                st.switch_page("pages/security.py")
        st.divider()

    
    if st.session_state.get("logged_in"):
        st.markdown(f"👋 **Welcome, {st.session_state.get('user', 'User')}!**")
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.switch_page("pages/security.py")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ New Chat", use_container_width=True):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.session_state.route_data = None
            st.rerun()
    with col2:
        if st.button("🗑 Clear", use_container_width=True):
            clear_chat(st.session_state.session_id)
            st.session_state.messages = []
            st.session_state.route_data = None
            st.rerun()

    st.markdown("#### 📜 History")
    sessions = list(dict.fromkeys(get_all_sessions()))
    for i, s in enumerate(sessions):
        label = f"▶ Chat {i+1}" if s == st.session_state.session_id else f"💬 Chat {i+1}"
        if st.button(label, key=f"session_{s}", use_container_width=True):
            st.session_state.session_id = s
            raw = load_messages(s)
            st.session_state.messages = [
                {"role": str(m.get("role", "user")), "content": str(m.get("content", ""))}
                for m in raw if isinstance(m, dict)
            ]
            st.session_state.route_data = None
            st.rerun()

   
    if st.session_state.route_data:
        rd = st.session_state.route_data
        seg = rd.get("segment", {})
        dist_km = seg.get("distance", 0) / 1000
        dur_min = seg.get("duration", 0) / 60
        st.divider()
        st.markdown(
            f"**🗺️ Last Route:**\n\n"
            f"📍 {rd.get('start', '?').title()} → {rd.get('end', '?').title()}\n\n"
            f"📏 {dist_km:.1f} km &nbsp;|&nbsp; ⏱ {dur_min:.0f} mins"
        )



st.title("✈️ Smart AI Travel Assistant")

chat_container = st.container()

with chat_container:
    messages_to_show = st.session_state.messages[-30:]
    total  = len(st.session_state.messages)
    offset = total - len(messages_to_show)

    for i, msg in enumerate(messages_to_show):
        role    = msg.get("role", "user")
        content = msg.get("content", "")
        if not content:
            continue
        with st.chat_message(role):
            st.markdown(content)

        
        actual_index = offset + i
        if (
            st.session_state.map_message_index is not None
            and actual_index == st.session_state.map_message_index
            and st.session_state.route_data
            and role == "assistant"
        ):
            try:
                show_map(st.session_state.route_data, st)
            except Exception as e:
                st.error(f"Map error: {e}")




query = st.chat_input("Ask: route / trip / hotels / flights / general...")

if query:
    with chat_container:
        st.chat_message("user").markdown(query)

    st.session_state.messages.append({"role": "user", "content": query})
    save_message(st.session_state.session_id, "user", query)

    query_lower = query.lower()

    # Memory
    user_memories  = load_memory(USER_ID)
    memory_context = ("User Info:\n" + "\n".join(user_memories)) if user_memories else ""

    memory = extract_memory(query)
    if memory and memory not in user_memories:
        save_memory(USER_ID, memory)

    
    flight_data = train_data = hotel_data = map_data = None

    # Flight
    if "flight" in query_lower or "flights" in query_lower or "fly" in query_lower:
        result      = handle_flight({"query": query})
        flight_data = result.get("output", "")

    # Train
    elif "train" in query_lower or "rail" in query_lower:
        raw        = train_tool(query)
        train_data = f"🚆 **Train Results:**\n\n{raw}\n\n👉 Need timing or booking help?"

    # Hotel
    elif "hotel" in query_lower or "stay" in query_lower:
        raw        = hotel_tool(query)
        hotel_data = f"🏨 **Hotel Results:**\n\n{raw}\n\n👉 Want budget or luxury options?"

    
    elif (
        " to " in query_lower
        and len(query.split()) <= 5
        and not any(k in query_lower for k in [
            "plan", "trip", "itinerary", "best", "time",
            "visit", "when", "what", "how", "tips", "weather",
            "should", "why", "which", "recommend", "suggest"
        ])
    ):
        map_data = handle_map({"query": query})

    
    is_trip     = any(k in query_lower for k in ["plan", "trip", "itinerary", "vacation", "days"])
    is_greeting = any(k in query_lower for k in ["hi", "hello", "hey"])

    full_response  = ""
    new_route_data = None

    with chat_container:
        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("⏳ _Processing..._")

            
            if flight_data:
                full_response = flight_data

            
            elif train_data:
                full_response = train_data

           
            elif hotel_data:
                full_response = hotel_data

            
            elif map_data and isinstance(map_data, dict):
                rd = map_data.get("route_data")
                if isinstance(rd, dict):
                    new_route_data = rd
                    seg = new_route_data.get("segment", {})
                    dist_km = seg.get("distance", 0) / 1000
                    dur_min = seg.get("duration", 0) / 60
                    start   = new_route_data.get("start", "?").title()
                    end     = new_route_data.get("end", "?").title()

                    full_response = (
                        f"🗺️ **Route: {start} → {end}**\n\n"
                        f"📏 Distance: {dist_km:.1f} km\n"
                        f"⏱️ Duration: {dur_min:.0f} mins"
                    )
                else:
                    full_response = map_data.get("output", "Route generated.")

                placeholder.markdown(full_response)

                
                if new_route_data:
                    try:
                        show_map(new_route_data, st)
                    except Exception as e:
                        st.error(f"Map error: {e}")

            
            elif is_trip:
                full_response = gemini(f"""{memory_context}

Create a detailed travel itinerary (6 points max) for:
{query}""")

            # Greeting
            elif is_greeting:
                full_response = gemini(
                    f"{memory_context}\nReply casually and warmly to: {query}"
                )

           
            else:
                full_response = gemini(f"""You are a smart AI travel assistant.
{memory_context}

Answer helpfully and clearly in 3-5 lines:
{query}""")

            if not full_response:
                full_response = "Sorry, I couldn't generate a response. Please try again."

            
            if not new_route_data:
                streamed = ""
                for line in full_response.strip().split("\n"):
                    for word in line.split():
                        streamed += word + " "
                        placeholder.markdown(streamed + "▌")
                        time.sleep(0.01)
                    streamed += "\n"
                    placeholder.markdown(streamed + "▌")
                placeholder.markdown(streamed)

    
    if new_route_data:
        st.session_state.route_data = new_route_data
        st.session_state.map_message_index = len(st.session_state.messages)

    
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    save_message(st.session_state.session_id, "assistant", full_response)
