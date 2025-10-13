import json
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="HeyGen — Realtime Avatar (Public)", page_icon="🎥", layout="centered")

# ── Your HeyGen API key must be set in .streamlit/secrets.toml:
# [HeyGen]
# heygen_api_key = "sk-..."
API_KEY = st.secrets["HeyGen"]["heygen_api_key"]

HEYGEN_BASE = "https://api.heygen.com/v1"

def fetch_interactive_avatars():
    """Get public Interactive Avatars from HeyGen Streaming API."""
    url = f"{HEYGEN_BASE}/streaming/avatar.list"
    r = requests.get(url, headers={"accept":"application/json", "x-api-key": API_KEY}, timeout=30)
    r.raise_for_status()
    payload = r.json()
    # Keep only ACTIVE & public items if present
    items = (payload.get("data") or [])
    items = [a for a in items if (a.get("status") == "ACTIVE")]
    # Build (label, id) pairs
    options = []
    for a in items:
        label = a.get("pose_name") or a.get("avatar_id")
        aid   = a.get("avatar_id")
        if aid and label:
            options.append((label, aid))
    # Deduplicate by id, preserve order
    seen, deduped = set(), []
    for label, aid in options:
        if aid in seen: 
            continue
        seen.add(aid)
        deduped.append((label, aid))
    return deduped

def create_streaming_token() -> str:
    """Create a session token for Streaming Avatar."""
    r = requests.post(
        f"{HEYGEN_BASE}/streaming.create_token",
        headers={"X-Api-Key": API_KEY, "Accept": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    token = (r.json().get("data") or {}).get("token")
    if not token:
        raise RuntimeError(f"No token in response: {r.text}")
    return token

st.title("🎥 HeyGen Streaming Avatar — Interactive (Live)")
st.caption("Dropdown is populated via API. Two-way mode enabled (mic).")

# 1) Load avatars from API (protected; not on GitHub)
with st.spinner("Loading available Interactive Avatars…"):
    avatar_choices = fetch_interactive_avatars()

if not avatar_choices:
    st.error("No Interactive Avatars returned. Please verify your HeyGen account has Streaming access.")
    st.stop()

labels = [lbl for (lbl, _id) in avatar_choices]
default_index = 0
label = st.selectbox("Choose an Interactive Avatar:", labels, index=default_index)
avatar_id = dict(avatar_choices)[label]

# 2) Choose a compatible voice (Mark) or let you type another
VOICE_ID = st.text_input("Voice ID (Interactive-compatible)", "f38a635bee7a4d1f9b0a654a31d050d2")

# 3) Create a streaming token
token = create_streaming_token()
st.info(f"Token OK (len={len(token)}). Prefix: {token[:8]}…")
st.success(f"Using avatar: {label}  •  id: {avatar_id}")

# 4) Inject values into the HTML client
with open("client.html", "r", encoding="utf-8") as f:
    html = f.read()

html = (
    html.replace("__TOKEN__", token)
        .replace("__AVATAR_ID__", avatar_id)
        .replace("__VOICE_ID__", VOICE_ID)
        .replace("__LINE1__", "Hello, how are you.")
        .replace("__LINE2__", "Welcome to our restaurant.")
        .replace("__LINE3__", "It is our pleasure serving you.")
)

components.html(html, height=820, scrolling=True)
