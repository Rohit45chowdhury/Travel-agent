import streamlit as st
import re
import sys
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from Backend.db import init_db, register_user, login_user

init_db()

st.title("🔐 Login & Signup")

st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

# ---------------- VALIDATION ----------------
def valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

# ---------------- TABS ----------------
tab1, tab2 = st.tabs(["🔐 Login", "📝 Signup"])

# ---------------- LOGIN TAB ----------------
with tab1:
    st.subheader("Login")

    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_pass")

    if st.button("Login", use_container_width=True):
        user = login_user(email, password)

        if user:
            st.session_state["user"] = user[0]
            st.session_state["logged_in"] = True
            st.success(f"Welcome {user[0]} 🎉")
            st.switch_page("main.py")  # ✅ chatbot pe wapas
        else:
            st.error("Invalid credentials")

# ---------------- SIGNUP TAB ----------------
with tab2:
    st.subheader("Create Account")

    name = st.text_input("Name", key="signup_name")
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_pass")

    if st.button("Signup", use_container_width=True):
        if len(name) < 3 or name.isnumeric():
            st.error("Name must be at least 3 characters & not numeric")
        elif not valid_email(email):
            st.error("Invalid Email")
        elif len(password) < 6:
            st.error("Password must be at least 6 characters")
        else:
            success = register_user(name, email, password)
            if success:
                st.success("✅ Account created! Please go to Login tab.")
            else:
                st.warning("Email already exists")