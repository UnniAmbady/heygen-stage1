import json
import time
import requests
import streamlit as st
from typing import Tuple, Dict, Any, Optional

st.set_page_config(page_title="HeyGen Streaming (REST API) — Diagnostics & Control", page_icon="🎥", layout="centered")

API_KEY = st.secrets["HeyGen"]["heygen_api_key"]
BASE = "https://api.heygen.com/v1"
HEADERS_JSON = {"accept": "application/json", "content-type": "application/json", "x-api-key": API_KEY}
HEADERS_GET  = {"accept": "application/json", "x-api-key": API_KEY}

# ---------------------------
# Helpers: HTTP + banners
# ---------------------------
def _post(url: str, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any], str]:
    r = requests.post(url, headers=HEADERS_JSON, json=payload, timeout=30)
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text}
    return r.status_code, body, r.text

def _get(url: str) -> Tuple[int, Dict[str, Any], str]:
    r = requests.get(url, headers=HEADERS_GET, timeout=30)
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text}
    return r.status_code, body, r.text

def banner_for_response(title: str, status: int, body: Dict[str, Any]) -> None:
    """Show a wide alert with success/failure based on HTTP status (200 good, 400 bad) and API code/message."""
    code = body.get("code")
    msg  = body.get("message") or body.get("error") or ""
    lines = [f"{title}",
             f"http_status: {status}",
             f"result: {'200 (success)' if status == 200 else '400/other (failure)'}"]
    if code is not None:
        lines.append(f"api_code: {code}")
    if msg:
        lines.append(f"api_message: {msg}")
    txt = "\n".join(lines)
    if status == 200:
        st.success(txt)
    else:
        st.error(txt, icon="🚨", width="stretch")

# ---------------------------
# REST: list avatars (for dropdown)
# ---------------------------
@st.cache_data(ttl=300)
def fetch_interactive_avatars():
    status, body, _ = _get(f"{BASE}/streaming/avatar.list")
    # Always show an interpretation banner per your request
    banner_for_response("avatar.list", status, body)
    data = body.get("data") or []
    items = []
    for a in data:
        if a.get("status") == "ACTIVE":
            items.append({
                "label": a.get("pose_name") or a.get("avatar_id"),
                "avatar_id": a.get("avatar_id"),
                "default_voice": a.get("default_voice"),
                "preview": a.get("normal_preview"),
                "is_public": a.get("is_public"),
            })
    # dedupe by id
    seen, out = set(), []
    for it in items:
        aid = it["avatar_id"]
        if aid and aid not in seen:
            seen.add(aid)
            out.append(it)
    return out

# ---------------------------
# REST: create token (step 0)
# ---------------------------
def create_session_token() -> Optional[str]:
    status, body, _ = _post(f"{BASE}/streaming.create_token", {})
    banner_for_response("create_token", status, body)
    if status != 200:
        return None
    return (body.get("data") or {}).get("token")

# ---------------------------
# REST: new session (step 1)
# ---------------------------
def new_session_payload(quality="medium", voice_rate=1, video_encoding="VP8") -> Dict[str, Any]:
    return {
        "quality": quality,
        "voice": {"rate": voice_rate},
        "video_encoding": video_encoding,
        "disable_idle_timeout": False,
        "version": "v2",
        "stt_settings": {"provider": "deepgram", "confidence": 0.55},
        "activity_idle_timeout": 120
    }

def new_session() -> Optional[Dict[str, Any]]:
    status, body, _ = _post(f"{BASE}/streaming.new", new_session_payload())
    banner_for_response("streaming.new", status, body)
    if status != 200:
        return None
    return body.get("data") or {}

# ---------------------------
# REST: start session (step 2)
# ---------------------------
def start_session(session_id: str) -> bool:
    status, body, _ = _post(f"{BASE}/streaming.start", {"session_id": session_id})
    # Per docs: success returns {} with HTTP 200; failure returns 400 with JSON
    banner_for_response("streaming.start", status, body)
    return status == 200

# ---------------------------
# REST: send task (speak)
# ---------------------------
def send_task(session_id: str, text: str) -> bool:
    status, body, _ = _post(f"{BASE}/streaming.task", {"session_id": session_id, "text": text})
    banner_for_response("streaming.task", status, body)
    return status == 200

# ---------------------------
# REST: list sessions (status)
# ---------------------------
def list_sessions() -> Dict[str, Any]:
    status, body, _ = _get(f"{BASE}/streaming.list")
    banner_for_response("streaming.list", status, body)
    return body

# ---------------------------
# REST: keep-alive
# ---------------------------
def keep_alive() -> bool:
    status, body, _ = _post(f"{BASE}/streaming.keep_alive", {})
    banner_for_response("streaming.keep_alive", status, body)
    return status == 200

# ---------------------------
# REST: stop session
# ---------------------------
def stop_session(session_id: str) -> bool:
    status, body, _ = _post(f"{BASE}/streaming.stop", {"session_id": session_id})
    banner_for_response("streaming.stop", status, body)
    return status == 200

# ---------------------------
# UI & State
# ---------------------------
if "session" not in st.session_state:
    st.session_state.session = None  # dict from streaming.new
if "avatar_selection" not in st.session_state:
    st.session_state.avatar_selection = None

st.title("🎥 HeyGen Streaming — REST API Control Board")
st.caption("Exact endpoints as in docs: new → start → task → list → keep_alive → stop. Strict 200/400 handling.")

# Avatar chooser
avatars = fetch_interactive_avatars()
if not avatars:
    st.stop()

labels = [a["label"] for a in avatars]
default_idx = 0 if st.session_state.avatar_selection is None else max(0, next((i for i,a in enumerate(avatars) if a["avatar_id"] == st.session_state.avatar_selection), 0))
label = st.selectbox("Choose an Interactive Avatar:", labels, index=default_idx, help="Changing avatar will stop the previous session, then create a fresh one.")

chosen = next(a for a in avatars if a["label"] == label)
avatar_id = chosen["avatar_id"]
default_voice = chosen["default_voice"]
preview = chosen["preview"]

# If avatar changed → stop old session (if any)
if st.session_state.avatar_selection and st.session_state.avatar_selection != avatar_id:
    old = st.session_state.session
    if old and old.get("session_id"):
        st.info("Avatar changed → stopping previous session…")
        stop_session(old["session_id"])
    st.session_state.session = None

st.session_state.avatar_selection = avatar_id

# Show preview
if preview:
    st.image(preview, caption=f"Preview • {label}", use_container_width=True)

st.divider()

# Controls row
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Step 0: Create Token (diagnostic)"):
        token = create_session_token()
        st.write("token length:", len(token) if token else 0)
with col2:
    if st.button("Step 1: Create New Session"):
        data = new_session()
        if data:
            # Persist the important bits into state
            st.session_state.session = {
                "session_id": data.get("session_id"),
                "realtime_endpoint": data.get("realtime_endpoint"),
                "url": data.get("url"),
                "access_token": data.get("access_token"),
                "livekit_agent_token": data.get("livekit_agent_token"),
                "created_at": time.time(),
                "avatar_id": avatar_id,
                "voice_id": default_voice,
            }
with col3:
    if st.button("Step 2: Start Session"):
        s = st.session_state.session
        if not s or not s.get("session_id"):
            st.error("No session_id. Click 'Step 1: Create New Session' first.", icon="🚨", width="stretch")
        else:
            ok = start_session(s["session_id"])
            if ok:
                st.success("Session started.", icon="✅")

st.divider()

# Speak / preview / keep-alive / stop
line1 = "Hello, how are you."
line2 = "Welcome to our restaurant."
line3 = "It is our pleasure serving you."

c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("Speak: Line 1"):
        s = st.session_state.session
        if not s or not s.get("session_id"):
            st.error("No active session. Create & start a session first.", icon="🚨", width="stretch")
        else:
            send_task(s["session_id"], line1)
with c2:
    if st.button("Speak: Line 2"):
        s = st.session_state.session
        if not s or not s.get("session_id"):
            st.error("No active session. Create & start a session first.", icon="🚨", width="stretch")
        else:
            send_task(s["session_id"], line2)
with c3:
    if st.button("Speak: Line 3"):
        s = st.session_state.session
        if not s or not s.get("session_id"):
            st.error("No active session. Create & start a session first.", icon="🚨", width="stretch")
        else:
            send_task(s["session_id"], line3)
with c4:
    if st.button("Preview Voice"):
        s = st.session_state.session
        if not s or not s.get("session_id"):
            st.error("No active session. Create & start a session first.", icon="🚨", width="stretch")
        else:
            send_task(s["session_id"], "This is a quick voice preview from the selected avatar.")

st.divider()

k1, k2 = st.columns(2)
with k1:
    if st.button("Keep Alive (Ping)"):
        keep_alive()
with k2:
    if st.button("Stop Session"):
        s = st.session_state.session
        if s and s.get("session_id"):
            stop_session(s["session_id"])
            st.session_state.session = None
        else:
            st.info("No active session to stop.")

st.divider()

# Current session status (streaming.list)
st.subheader("Current Sessions (server view)")
body = list_sessions()
sessions = ((body.get("data") or {}).get("sessions") or [])
if not sessions:
    st.write("No active sessions.")
else:
    st.write(sessions)

# Footer: show what we are tying to (for your records)
s = st.session_state.session
if s:
    st.caption(f"Session: {s['session_id']} • Avatar: {s['avatar_id']} • Voice: {s['voice_id']}")
    st.caption(f"Endpoint: {s['realtime_endpoint']} • URL: {s['url']}")
