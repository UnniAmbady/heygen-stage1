import json
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="HeyGen — Realtime Avatar (Public)", page_icon="🎥", layout="centered")

API_KEY = st.secrets["HeyGen"]["heygen_api_key"]
HEYGEN_BASE = "https://api.heygen.com/v1"

def fetch_interactive_avatars():
    """Return a list of dicts: [{label, avatar_id, default_voice}] via streaming/avatar.list."""
    url = f"{HEYGEN_BASE}/streaming/avatar.list"
    r = requests.get(url, headers={"accept": "application/json", "X-Api-Key": API_KEY}, timeout=600)
    r.raise_for_status()
    data = r.json().get("data") or []
    out = []
    for a in data:
        if a.get("status") != "ACTIVE":
            continue
        out.append({
            "label": a.get("pose_name") or a.get("avatar_id"),
            "avatar_id": a.get("avatar_id"),
            "default_voice": a.get("default_voice") or "",  # may be empty on some entries
        })
    # de-dup by avatar_id while preserving order
    seen, deduped = set(), []
    for item in out:
        aid = item["avatar_id"]
        if not aid or aid in seen:
            continue
        seen.add(aid)
        deduped.append(item)
    return deduped

def create_streaming_token() -> str:
    r = requests.post(
        f"{HEYGEN_BASE}/streaming.create_token",
        headers={"X-Api-Key": API_KEY, "Accept": "application/json"},
        timeout=600,
    )
    r.raise_for_status()
    token = (r.json().get("data") or {}).get("token")
    if not token:
        raise RuntimeError(f"No token in response: {r.text}")
    return token

st.title("🎥 HeyGen Streaming Avatar — Interactive (Live)")
st.caption("Avatars are loaded via API. Voice is auto-selected from the avatar’s default_voice.")

with st.spinner("Loading available Interactive Avatars…"):
    avatars = fetch_interactive_avatars()

if not avatars:
    st.error("No Interactive Avatars returned. Verify your HeyGen account has Streaming access.")
    st.stop()

labels = [a["label"] for a in avatars]
idx = 0
label = st.selectbox("Choose an Interactive Avatar:", labels, index=idx)
chosen = next(a for a in avatars if a["label"] == label)
avatar_id = chosen["avatar_id"]
voice_id = chosen["default_voice"] or "f38a635bee7a4d1f9b0a654a31d050d2"  # fallback if API omits it

token = create_streaming_token()
st.info(f"Token OK (len={len(token)}). Prefix: {token[:8]}…")
st.success(f"Using avatar: {label}  •  id: {avatar_id}  •  voice: {voice_id[:8]}…")

with open("client.html", "r", encoding="utf-8") as f:
    html = f.read()

html = (html
        .replace("__TOKEN__", token)
        .replace("__AVATAR_ID__", avatar_id)
        .replace("__VOICE_ID__", voice_id)
        .replace("__LINE1__", "Hello, how are you.")
        .replace("__LINE2__", "Welcome to our restaurant.")
        .replace("__LINE3__", "It is our pleasure serving you.")
)

components.html(html, height=820, scrolling=True)
