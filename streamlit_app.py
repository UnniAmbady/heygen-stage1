import json
import requests
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(page_title="HeyGen — Realtime Avatar Demo", page_icon="🎥", layout="centered")

API_KEY = st.secrets["HeyGen"]["heygen_api_key"]

# --- Read public Interactive Avatars list and pick the FIRST item ---
def get_default_public_avatar_id():
    try:
        data = json.loads((Path(__file__).parent / "Public AVATAR.json").read_text(encoding="utf-8"))
        first = (data.get("data") or [])[0]
        return first.get("avatar_id")
    except Exception:
        return None

DEFAULT_PUBLIC_AVATAR_ID = get_default_public_avatar_id() or ""

# “Mark” voice (interactive-compatible), per HeyGen’s note
VOICE_ID = "f38a635bee7a4d1f9b0a654a31d050d2"

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

st.title("🎥 HeyGen Streaming Avatar — Live Proof (Public Interactive Avatar)")
st.caption("Uses a public Interactive Avatar (first item in your JSON). Click a button to speak — real-time, no rendering.")

token = create_session_token()
st.info(f"Token prefix: {token[:8]}…  (streaming token created)")

# Force the first public Interactive Avatar from your JSON
avatar_id_for_streaming = DEFAULT_PUBLIC_AVATAR_ID
if avatar_id_for_streaming:
    st.success(f"Using public avatar: {avatar_id_for_streaming}")
else:
    st.warning("Could not read avatar from 'Public AVATAR.json'. Falling back to HeyGen’s default public avatar.")

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
