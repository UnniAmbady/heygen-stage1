import requests
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(page_title="HeyGen — Realtime Avatar Demo", page_icon="🎥", layout="centered")

AVATAR_ID = "bf01e45ed0c04fe6958ca6551ce17ca0"
VOICE_ID  = "f38a635bee7a4d1f9b0a654a31d050d2"  # Public "Mark"
API_KEY   = st.secrets["HeyGen"]["heygen_api_key"]

def create_session_token() -> str:
    r = requests.post(
        "https://api.heygen.com/v1/streaming.create_token",
        headers={"X-Api-Key": API_KEY, "Accept": "application/json"},
        timeout=15,
    )
    r.raise_for_status()
    token = (r.json().get("data") or {}).get("token")
    if not token:
        raise RuntimeError(f"No session token in response: {r.text}")
    return token

st.title("🎥 HeyGen Streaming Avatar — Live Proof")
st.caption("One live session (low/≈720p). Click a button to speak. No rendering, no emails.")

token = create_session_token()  # if plan blocked, you'll get HTTP 4xx here
st.info(f"Token prefix: {token[:8]}…")  # remove after testing

# Load the static HTML file
html_path = Path(__file__).parent / "client.html"
html = html_path.read_text(encoding="utf-8")

# Inject values with simple .replace on plain strings
html = (html
        .replace("__TOKEN__", token)
        .replace("__AVATAR_ID__", AVATAR_ID)
        .replace("__VOICE_ID__", VOICE_ID)
        .replace("__LINE1__", "Hello, how are you.")
        .replace("__LINE2__", "Welcome to our restaurant.")
        .replace("__LINE3__", "It is our pleasure serving you.")
)

components.html(html, height=620)

