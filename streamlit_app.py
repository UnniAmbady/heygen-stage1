import requests
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(page_title="HeyGen — Realtime Avatar Demo", page_icon="🎥", layout="centered")

# Your working IDs (keep for later)
MY_AVATAR_ID = "bf01e45ed0c04fe6958ca6551ce17ca0"   # may NOT be streaming-enabled
VOICE_ID     = "f38a635bee7a4d1f9b0a654a31d050d2"   # Public "Mark"

# ---- Toggle this: start with False to use a public streaming avatar
USE_MY_AVATAR_FOR_STREAMING = False

API_KEY = st.secrets["HeyGen"]["heygen_api_key"]

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
st.caption("One live session (~720p). Click a button to speak — no rendering, no emails.")

token = create_session_token()
st.info(f"Token prefix: {token[:8]}…  (proves your plan/key can create stream tokens)")

# For the first run, leave avatar id empty => default public streaming avatar
avatar_id_for_streaming = MY_AVATAR_ID if USE_MY_AVATAR_FOR_STREAMING else ""

# Load client and inject plain strings
html = (Path(__file__).parent / "client.html").read_text(encoding="utf-8")
html = (html
        .replace("__TOKEN__", token)
        .replace("__AVATAR_ID__", avatar_id_for_streaming)
        .replace("__VOICE_ID__", VOICE_ID)
        .replace("__LINE1__", "Hello, how are you.")
        .replace("__LINE2__", "Welcome to our restaurant.")
        .replace("__LINE3__", "It is our pleasure serving you.")
)

components.html(html, height=720)
