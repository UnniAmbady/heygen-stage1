import json
import time
import base64
import requests
import streamlit as st
from typing import Tuple, Dict, Any, Optional

st.set_page_config(page_title="HeyGen Streaming (REST) — Control Panel", page_icon="🎥", layout="centered")

API_KEY = st.secrets["HeyGen"]["heygen_api_key"]
BASE = "https://api.heygen.com/v1"

HEADERS_GET  = {"accept": "application/json", "x-api-key": API_KEY}
HEADERS_JSON = {"accept": "application/json", "content-type": "application/json", "x-api-key": API_KEY}
HEADERS_NOBODY = {"accept": "application/json", "x-api-key": API_KEY}  # for keep_alive (no JSON body)

# ---------------------------
# Helpers: HTTP + banners
# ---------------------------
def _post_json(url: str, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any], str]:
    r = requests.post(url, headers=HEADERS_JSON, json=payload, timeout=30)
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text}
    return r.status_code, body, r.text

def _post_nobody(url: str) -> Tuple[int, Dict[str, Any], str]:
    r = requests.post(url, headers=HEADERS_NOBODY, timeout=30)  # NO BODY
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
    """Show success on HTTP 200, error otherwise. Also surface api_code/message when present."""
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
    (st.success if status == 200 else (lambda t: st.error(t, icon='🚨', width='stretch')))(txt)

# ---------------------------
# REST endpoints (exact per docs)
# ---------------------------
@st.cache_data(ttl=300)
def fetch_interactive_avatars():
    status, body, _ = _get(f"{BASE}/streaming/avatar.list")
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
    # dedupe
    seen, out = set(), []
    for it in items:
        aid = it["avatar_id"]
        if aid and aid not in seen:
            seen.add(aid)
            out.append(it)
    return out

def create_session_token() -> Optional[str]:
    status, body, _ = _post_json(f"{BASE}/streaming.create_token", {})
    banner_for_response("create_token", status, body)
    if status != 200:
        return None
    return (body.get("data") or {}).get("token")

def new_session() -> Optional[Dict[str, Any]]:
    payload = {
        "quality": "medium",
        "voice": { "rate": 1 },
        "video_encoding": "VP8",
        "disable_idle_timeout": False,
        "version": "v2",
        "stt_settings": { "provider": "deepgram", "confidence": 0.55 },
        "activity_idle_timeout": 120
    }
    status, body, _ = _post_json(f"{BASE}/streaming.new", payload)
    banner_for_response("streaming.new", status, body)
    if status != 200:
        return None
    return body.get("data") or {}

def start_session(session_id: str) -> bool:
    status, body, _ = _post_json(f"{BASE}/streaming.start", { "session_id": session_id })
    banner_for_response("streaming.start", status, body)
    return status == 200

def send_task(session_id: str, text: str) -> bool:
    status, body, _ = _post_json(f"{BASE}/streaming.task", { "session_id": session_id, "text": text })
    banner_for_response("streaming.task", status, body)
    return status == 200

def list_sessions() -> Dict[str, Any]:
    status, body, _ = _get(f"{BASE}/streaming.list")
    banner_for_response("streaming.list", status, body)
    return body

def keep_alive() -> bool:
    status, body, _ = _post_nobody(f"{BASE}/streaming.keep_alive")  # NO JSON BODY
    banner_for_response("streaming.keep_alive", status, body)
    return status == 200

def stop_session(session_id: str) -> bool:
    status, body, _ = _post_json(f"{BASE}/streaming.stop", { "session_id": session_id })
    banner_for_response("streaming.stop", status, body)
    return status == 200

# ---------------------------
# State
# ---------------------------
if "session" not in st.session_state:
    st.session_state.session = None
if "avatar_selection" not in st.session_state:
    st.session_state.avatar_selection = None

# ---------------------------
# UI
# ---------------------------
st.title("🎥 HeyGen Streaming — Control Panel (REST) + Phone Viewer")
st.caption("Use this page to create/start/stop sessions and send tasks. Open the phone-sized viewer in a popup.")

avatars = fetch_interactive_avatars()
if not avatars:
    st.stop()

labels = [a["label"] for a in avatars]
default_idx = 0 if st.session_state.avatar_selection is None else max(
    0, next((i for i,a in enumerate(avatars) if a["avatar_id"] == st.session_state.avatar_selection), 0)
)
label = st.selectbox("Choose an Interactive Avatar:", labels, index=default_idx,
                     help="Changing avatar stops the previous session, then creates a fresh one.")
chosen = next(a for a in avatars if a["label"] == label)
avatar_id = chosen["avatar_id"]
voice_id  = chosen["default_voice"]
preview   = chosen["preview"]

# If avatar changed → stop prior session
if st.session_state.avatar_selection and st.session_state.avatar_selection != avatar_id:
    old = st.session_state.session
    if old and old.get("session_id"):
        st.info("Avatar changed → stopping previous session first…")
        stop_session(old["session_id"])
    st.session_state.session = None
st.session_state.avatar_selection = avatar_id

if preview:
    st.image(preview, caption=f"Preview • {label}", use_container_width=True)

st.divider()

# Controls
col0, col1, col2, col3 = st.columns(4)
with col0:
    if st.button("Step 0: Create Token (diagnostic)"):
        tok = create_session_token()
        st.write("token length:", len(tok) if tok else 0)

with col1:
    if st.button("Step 1: Create New Session"):
        data = new_session()
        if data:
            st.session_state.session = {
                "session_id": data.get("session_id"),
                "realtime_endpoint": data.get("realtime_endpoint"),
                "url": data.get("url"),
                "access_token": data.get("access_token"),
                "livekit_agent_token": data.get("livekit_agent_token"),
                "created_at": time.time(),
                "avatar_id": avatar_id,
                "voice_id": voice_id,
            }

with col2:
    if st.button("Step 2: Start Session"):
        s = st.session_state.session
        if not s or not s.get("session_id"):
            st.error("No session_id. Click 'Step 1: Create New Session' first.", icon="🚨", width="stretch")
        else:
            if start_session(s["session_id"]):
                st.success("Session started.", icon="✅")

with col3:
    if st.button("Stop Session"):
        s = st.session_state.session
        if s and s.get("session_id"):
            stop_session(s["session_id"])
            st.session_state.session = None
        else:
            st.info("No active session to stop.")

st.divider()

# Speak / Keep-alive row
line1 = "Hello, how are you."
line2 = "Welcome to our restaurant."
line3 = "It is our pleasure serving you."

c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("Speak • Line 1"):
        s = st.session_state.session
        st.error("No active session. Create & start a session first.", icon="🚨", width="stretch") if not s or not s.get("session_id") else send_task(s["session_id"], line1)
with c2:
    if st.button("Speak • Line 2"):
        s = st.session_state.session
        st.error("No active session. Create & start a session first.", icon="🚨", width="stretch") if not s or not s.get("session_id") else send_task(s["session_id"], line2)
with c3:
    if st.button("Speak • Line 3"):
        s = st.session_state.session
        st.error("No active session. Create & start a session first.", icon="🚨", width="stretch") if not s or not s.get("session_id") else send_task(s["session_id"], line3)
with c4:
    if st.button("Keep Alive (Ping)"):
        keep_alive()

st.divider()

# --- Phone-sized popup viewer ---
st.subheader("Open Viewer (Phone-sized Pop-up)")

# Create a fresh streaming token for the viewer so we don't expose API key client-side.
viewer_token = create_session_token() or ""
with open("client.html", "r", encoding="utf-8") as f:
    client_html = f.read()

client_html = (client_html
               .replace("__TOKEN__", viewer_token)
               .replace("__AVATAR_ID__", avatar_id)
               .replace("__VOICE_ID__", voice_id))

# Build a data URL to pass into a JS popup window.
data_url = "data:text/html;base64," + base64.b64encode(client_html.encode("utf-8")).decode("ascii")

popup_js = f"""
<script>
  function openAvatarPopup() {{
    const w = 420, h = 760;
    const left = window.screenX + Math.max(0, (window.outerWidth - w) / 2);
    const top  = window.screenY + Math.max(0, (window.outerHeight - h) / 2);
    const opts = `width=${{w}},height=${{h}},left=${{left}},top=${{top}},resizable=yes,menubar=no,toolbar=no,location=no,status=no`;
    window.open("{data_url}", "heygen_viewer", opts);
  }}
</script>
<button onclick="openAvatarPopup()" style="padding:10px 14px;border-radius:10px;border:1px solid #ddd;cursor:pointer;">Open Avatar Viewer (Phone)</button>
"""

st.components.v1.html(popup_js, height=60)

st.divider()

# Current session list (server view)
st.subheader("Current Sessions (server view)")
body = list_sessions()
sessions = ((body.get("data") or {}).get("sessions") or [])
if not sessions:
    st.write("No active sessions.")
else:
    st.write(sessions)

# Footer
s = st.session_state.session
if s:
    st.caption(f"Session: {s['session_id']} • Avatar: {s['avatar_id']} • Voice: {s['voice_id']}")
    st.caption(f"Endpoint: {s['realtime_endpoint']} • URL: {s['url']}")

