import json
import requests
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
from urllib.parse import quote

st.set_page_config(page_title="HeyGen — Realtime Avatar (Public)", page_icon="🎥", layout="centered")

API_KEY = st.secrets["HeyGen"]["heygen_api_key"]

def read_first_public_avatar_id():
    try:
        data = json.loads((Path(__file__).parent / "Public AVATAR.json").read_text(encoding="utf-8"))
        return (data.get("data") or [])[0].get("avatar_id", "")
    except Exception:
        return ""

PUBLIC_AVATAR_ID = read_first_public_avatar_id()
VOICE_ID = "f38a635bee7a4d1f9b0a654a31d050d2"  # “Mark”

def create_streaming_token() -> str:
    r = requests.post(
        "https://api.heygen.com/v1/streaming.create_token",
        headers={"X-Api-Key": API_KEY, "Accept": "application/json"},
        timeout=20,
    )
    r.raise_for_status()
    token = (r.json().get("data") or {}).get("token")
    if not token:
        raise RuntimeError(f"No token in response: {r.text}")
    return token

st.title("🎥 HeyGen Streaming Avatar — Live Proof (Public Interactive Avatar)")
st.caption("Uses a public Interactive Avatar (first item in your JSON).")

token = create_streaming_token()
st.info(f"Token prefix: {token[:8]}…  (streaming token created)")
st.success(f"Using public avatar: {PUBLIC_AVATAR_ID or '<<not found>>'}")

# Load HTML shell and inject runtime values (kept as a separate file as requested)
html = (Path(__file__).parent / "client.html").read_text(encoding="utf-8")
html = (html
        .replace("__TOKEN__", token)
        .replace("__AVATAR_ID__", PUBLIC_AVATAR_ID)
        .replace("__VOICE_ID__", VOICE_ID)
        .replace("__LINE1__", "Hello, how are you.")
        .replace("__LINE2__", "Welcome to our restaurant.")
        .replace("__LINE3__", "It is our pleasure serving you.")
)

# Provide an “open in new tab” button in case the Streamlit iframe blocks WebRTC
data_url = "data:text/html;charset=utf-8," + quote(html)
st.link_button("🔗 Open client in a new tab (bypass iframe)", data_url)

components.html(html, height=760, scrolling=True)

