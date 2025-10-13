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

# ---------- HTTP helpers ----------
def _post_json(url: str, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any], str]:
    r = requests.post(url, headers=HEADERS_JSON, json=payload, timeout=30)
    try: body = r.json()
    except Exception: body = {"raw": r.text}
    return r.status_code, body, r.text

def _post_nobody(url: str) -> Tuple[int, Dict[str, Any], str]:
    r = requests.post(url, headers=HEADERS_NOBODY, timeout=30)  # NO BODY
    try: body = r.json()
    except Exception: body = {"raw": r.text}
    return r.status_code, body, r.text

def _get(url: str) -> Tuple[int, Dict[str, Any], str]:
    r = requests.get(url, headers=HEADERS_GET, timeout=30)
    try: body = r.json()
    except Exception: body = {"raw": r.text}
    return r.status_code, body, r.text

def banner_for_response(title: str, status: int, body: Dict[str, Any]) -> None:
    code = body.get("code")
    msg  = body.get("message") or body.get("error") or ""
    lines = [f"{title}",
             f"http_status: {status}",
             f"result: {'200 (success)' if status == 200 else '400/other (failure)'}"]
    if code is not None: lines.append(f"api_code: {code}")
    if msg: lines.append(f"api_message: {msg}")
    txt = "\n".join(lines)
    (st.success if status == 200 else (lambda t: st.error(t, icon='🚨', width='stretch')))(txt)

# ---------- REST endpoints ----------
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
    if status != 200: return None
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
    if status != 200: return None
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

# ---------- State ----------
if "session" not in st.session_state: st.session_state.session = None
if "avatar_selection" not in st.session_state: st.session_state.avatar_selection = None

# ---------- UI ----------
st.title("🎥 HeyGen Streaming — Control Panel (REST) + Inline Phone Viewer")
st.caption("Create/start/stop sessions and send tasks. A phone-sized viewer is embedded below.")

avatars = fetch_interactive_avatars()
if not avatars: st.stop()

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

# If avatar changed → stop old session
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

# -------- Inline Viewer (phone-sized) ----------
st.subheader("Inline Viewer (Phone frame)")

viewer_token = create_session_token() or ""
viewer_html = f"""
<!doctype html>
<html>
  <head>
    <meta charset='utf-8' />
    <meta name='viewport' content='width=device-width, initial-scale=1, viewport-fit=cover' />
    <style>
      html,body {{ height:100%; margin:0; background:#000; }}
      #wrap {{ position:fixed; inset:0; display:grid; grid-template-rows:auto 1fr; width:420px; max-width:100%; height:760px; margin:auto; border-radius:22px; overflow:hidden; box-shadow:0 10px 30px rgba(0,0,0,.35); }}
      #status {{ color:#bbb; font:14px/1.2 system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; padding:8px 10px; background:#111; }}
      video {{ width:100%; height:100%; object-fit:contain; background:#000; }}
      #tap {{ position:absolute; right:12px; bottom:12px; color:#111; background:#fff; padding:6px 10px; border-radius:999px; font:12px system-ui; display:none; }}
    </style>
  </head>
  <body>
    <div id="wrap">
      <div id="status">Connecting…</div>
      <video id="v" autoplay playsinline muted></video>
      <div id="tap">tap to unmute</div>
    </div>
    <script type="module">
      import * as SDK from "https://cdn.jsdelivr.net/npm/@heygen/streaming-avatar/+esm";
      const {{ StreamingAvatar, StreamingEvents }} = SDK;
      const TOKEN="{viewer_token}";
      const AVATAR="{avatar_id}";
      const VOICE="{voice_id}";
      const v = document.getElementById('v');
      const status = document.getElementById('status');
      const tap = document.getElementById('tap');
      const show = (t)=> status.textContent=t;

      const avatar = new StreamingAvatar({{ token: TOKEN }});
      if (avatar.setVideoElement) {{ try {{ avatar.setVideoElement(v); }} catch(e) {{}} }}

      avatar.on(StreamingEvents.STREAM_READY, (evt) => {{
        if (evt?.detail) v.srcObject = evt.detail;
        show("Live");
        tap.style.display = "inline-block";
      }});
      avatar.on(StreamingEvents.ERROR, (evt) => {{
        const err = evt?.detail || evt; show("Error — see console"); console.error("SDK error:", err);
      }});
      avatar.on(StreamingEvents.STREAM_DISCONNECTED, () => show("Disconnected"));

      (async () => {{
        try {{
          await avatar.createStartAvatar({{ avatarId: AVATAR, quality: "low", voice: {{ voice_id: VOICE }} }});
        }} catch(e) {{
          show("Start failed"); console.error(e);
        }}
      }})();

      const tryUnmute = async () => {{ try {{ v.muted=false; await v.play(); tap.style.display='none'; }} catch(e){{}} }};
      tap.addEventListener('click', tryUnmute);
      v.addEventListener('click', tryUnmute);
      document.body.addEventListener('touchstart', tryUnmute, {{ once:true }});
    </script>
  </body>
</html>
"""
st.components.v1.html(viewer_html, height=800, scrolling=False)

st.divider()

# Current sessions
st.subheader("Current Sessions (server view)")
body = list_sessions()
sessions = ((body.get("data") or {}).get("sessions") or [])
st.write("No active sessions." if not sessions else sessions)

# Footer
s = st.session_state.session
if s:
    st.caption(f"Session: {s['session_id']} • Avatar: {s['avatar_id']} • Voice: {s['voice_id']}")
    st.caption(f"Endpoint: {s['realtime_endpoint']} • URL: {s['url']}")
