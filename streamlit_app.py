import json
import requests
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(page_title="HeyGen — Realtime Avatar Demo", page_icon="🎥", layout="centered")

# Your working IDs
AVATAR_ID = "bf01e45ed0c04fe6958ca6551ce17ca0"
VOICE_ID  = "f38a635bee7a4d1f9b0a654a31d050d2"  # public "Mark"

HEYGEN_API_KEY = st.secrets["HeyGen"]["heygen_api_key"]

def create_session_token() -> str:
    url = "https://api.heygen.com/v1/streaming.create_token"
    headers = {"X-Api-Key": HEYGEN_API_KEY, "Accept": "application/json"}
    r = requests.post(url, headers=headers, timeout=15)
    r.raise_for_status()
    token = (r.json().get("data") or {}).get("token")
    if not token:
        raise RuntimeError(f"No session token in response: {r.text}")
    return token

st.title("🎥 HeyGen Streaming Avatar — Live Proof")
st.caption("One live session at low/720p quality. Click a button and the avatar speaks immediately — no rendering, no emails.")

# Create a short-lived session token programmatically
token = create_session_token()

# Lines are kept in Python (no braces)
line1 = "Hello, how are you."
line2 = "Welcome to our restaurant."
line3 = "It is our pleasure serving you."

# Read static client HTML (no f-strings)
client_path = Path(__file__).parent / "client.html"
html = client_path.read_text(encoding="utf-8")

# Inject values safely with simple replacements (strings only)
html = (html
        .replace("__TOKEN__", token)
        .replace("__AVATAR_ID__", AVATAR_ID)
        .replace("__VOICE_ID__", VOICE_ID)
        .replace("__LINE1__", line1)
        .replace("__LINE2__", line2)
        .replace("__LINE3__", line3)
)

components.html(html, height=620)
