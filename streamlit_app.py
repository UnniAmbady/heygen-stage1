import json
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="HeyGen — Realtime Avatar Demo", page_icon="🎥", layout="centered")

# Fixed IDs
AVATAR_ID = "bf01e45ed0c04fe6958ca6551ce17ca0"
VOICE_ID  = "f38a635bee7a4d1f9b0a654a31d050d2"  # Public "Mark"

HEYGEN_API_KEY = st.secrets["HeyGen"]["heygen_api_key"]

def create_session_token():
    url = "https://api.heygen.com/v1/streaming.create_token"
    headers = {"X-Api-Key": HEYGEN_API_KEY, "Accept": "application/json"}
    r = requests.post(url, headers=headers, timeout=15)
    r.raise_for_status()
    token = (r.json().get("data") or {}).get("token")
    if not token:
        raise RuntimeError(f"No session token in response: {r.text}")
    return token

token = create_session_token()

st.title("🎥 HeyGen Streaming Avatar — Live Proof")
st.caption("One live session. Click a button to speak. No rendering, no emails.")

# Put lines as separate strings (no braces)
line1 = "Hello, how are you."
line2 = "Welcome to our restaurant."
line3 = "It is our pleasure serving you."

# Plain string (NOT f-string). No unquoted {{braces}} anywhere.
html_template = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; }
      #wrap { display: grid; gap: 12px; max-width: 840px; margin: 0 auto; }
      video { width: 100%; aspect-ratio: 16/9; background: #000; border-radius: 12px; }
      .row { display: grid; gap: 8px; grid-template-columns: repeat(3, 1fr); }
      button { padding: 10px 12px; border-radius: 10px; border: 1px solid #ddd; cursor: pointer; }
      button:disabled { opacity: 0.5; cursor: not-allowed; }
      .muted { font-size: 12px; color: #666; }
      .toprow { display:flex; gap:8px; align-items:center; }
    </style>
  </head>
  <body>
    <div id="wrap">
      <div class="toprow">
        <button id="unmuteBtn">Unmute audio</button>
        <div class="muted" id="status">Initializing stream…</div>
      </div>
      <video id="avatarVideo" autoplay playsinline muted></video>
      <div class="row">
        <button id="btn1" disabled>Say line 1</button>
        <button id="btn2" disabled>Say line 2</button>
        <button id="btn3" disabled>Say line 3</button>
      </div>
    </div>

    <!-- Streaming Avatar SDK -->
    <script type="module">
      import * as SDK from "https://cdn.jsdelivr.net/npm/@heygen/streaming-avatar/+esm";
      const StreamingAvatar = SDK.StreamingAvatar;
      const TaskType = SDK.TaskType;
      const StreamingEvents = SDK.StreamingEvents;

      // Dynamic values injected as plain strings (no braces in Python)
      const TOKEN    = "__TOKEN__";
      const AVATARID = "__AVATAR_ID__";
      const VOICEID  = "__VOICE_ID__";
      const LINE1    = "__LINE1__";
      const LINE2    = "__LINE2__";
      const LINE3    = "__LINE3__";

      const videoEl = document.getElementById('avatarVideo');
      const statusEl = document.getElementById('status');
      const unmuteBtn = document.getElementById('unmuteBtn');
      const btns = [document.getElementById('btn1'), document.getElementById('btn2'), document.getElementById('btn3')];

      // Token passed as a string — create the client with a JSON.parse to avoid braces in Python
      const avatar = new StreamingAvatar(JSON.parse('{"token":"'+TOKEN+'"}'));
      let sessionId = null;

      unmuteBtn.addEventListener('click', async () => {
        try { videoEl.muted = false; await videoEl.play(); unmuteBtn.disabled = true; unmuteBtn.textContent = "Audio unmuted"; }
        catch (e) { console.warn("Autoplay unblock failed:", e); }
      });

      avatar.on(StreamingEvents.STREAM_READY, (evt) => {
        videoEl.srcObject = evt.detail;
        statusEl.textContent = "Avatar is live. Click a button to speak.";
        btns.forEach(b => b.disabled = false);
      });

      avatar.on(StreamingEvents.AVATAR_START_TALKING, () => { statusEl.textContent = "Speaking…"; });
      avatar.on(StreamingEvents.AVATAR_STOP_TALKING, () => { statusEl.textContent = "Idle. Click again."; });

      (async () => {
        try {
          // Build options as string then parse — no braces in Python layer
          const opts = JSON.parse('{"avatarId":"'+AVATARID+'","quality":"low","voice":{"voice_id":"'+VOICEID+'"}}');
          const res = await avatar.createStartAvatar(opts);
          sessionId = res.session_id;
        } catch (err) {
          console.error(err);
          statusEl.textContent = "Failed to start session. Open console.";
        }
      })();

      const speak = async (text) => {
        try {
          const payload = JSON.parse('{"sessionId":"'+sessionId+'","text":"'+text+'","task_type":"REPEAT"}');
          await avatar.speak(payload);
        } catch (err) {
          console.error(err);
          statusEl.textContent = "Speak failed. See console.";
        }
      };
      btns[0].addEventListener('click', () => speak(LINE1));
      btns[1].addEventListener('click', () => speak(LINE2));
      btns[2].addEventListener('click', () => speak(LINE3));
    </script>
  </body>
</html>
"""

# Inject values safely (simple string replace — no braces evaluated by Python)
html = (
    html_template
      .replace("__TOKEN__", token)
      .replace("__AVATAR_ID__", AVATAR_ID)
      .replace("__VOICE_ID__", VOICE_ID)
      .replace("__LINE1__", line1)
      .replace("__LINE2__", line2)
      .replace("__LINE3__", line3)
)

components.html(html, height=600)
