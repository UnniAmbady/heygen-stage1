import json
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="HeyGen — Realtime Avatar Demo", page_icon="🎥", layout="centered")

# Fixed IDs (your working ones)
AVATAR_ID = "bf01e45ed0c04fe6958ca6551ce17ca0"
VOICE_ID  = "f38a635bee7a4d1f9b0a654a31d050d2"  # Public "Mark"

HEYGEN_API_KEY = st.secrets["HeyGen"]["heygen_api_key"]

def create_session_token():
    url = "https://api.heygen.com/v1/streaming.create_token"
    headers = {"X-Api-Key": HEYGEN_API_KEY, "Accept": "application/json"}
    r = requests.post(url, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json().get("data", {})
    token = data.get("token")
    if not token:
        raise RuntimeError(f"No session token in response: {r.text}")
    return token

session_token = create_session_token()

st.title("🎥 HeyGen Streaming Avatar — Live Proof")
st.caption("One live session. Click a button to speak. No rendering, no emails.")

cfg = {
    "token": session_token,
    "avatar_id": AVATAR_ID,
    "voice_id": VOICE_ID,
    "lines": [
        "Hello, how are you.",
        "Welcome to our restaurant.",
        "It is our pleasure serving you."
    ]
}

# HTML (NOT an f-string) — we inject the JSON config by replacing a marker.
html_template = r"""
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
    </style>
  </head>
  <body>
    <div id="wrap">
      <video id="avatarVideo" autoplay playsinline muted></video>
      <div class="row">
        <button id="btn1" disabled>Say line 1</button>
        <button id="btn2" disabled>Say line 2</button>
        <button id="btn3" disabled>Say line 3</button>
      </div>
      <div class="muted" id="status">Initializing stream…</div>
    </div>

    <!-- Config from Streamlit -->
    <script id="cfg" type="application/json">__CFG_JSON__</script>

    <!-- Streaming Avatar SDK from CDN -->
    <script type="module">
      import { StreamingAvatar, TaskType, StreamingEvents } from "https://cdn.jsdelivr.net/npm/@heygen/streaming-avatar/+esm";

      const cfg = JSON.parse(document.getElementById('cfg').textContent);
      const videoEl = document.getElementById('avatarVideo');
      const statusEl = document.getElementById('status');
      const btns = [document.getElementById('btn1'), document.getElementById('btn2'), document.getElementById('btn3')];

      const avatar = new StreamingAvatar({ token: cfg.token });
      let sessionId = null;

      avatar.on(StreamingEvents.STREAM_READY, (evt) => {
        videoEl.srcObject = evt.detail;
        videoEl.muted = false;  // hear it
        statusEl.textContent = "Avatar is live. Click a button to speak.";
        btns.forEach(b => b.disabled = false);
      });

      avatar.on(StreamingEvents.AVATAR_START_TALKING, () => { statusEl.textContent = "Speaking…"; });
      avatar.on(StreamingEvents.AVATAR_STOP_TALKING, () => { statusEl.textContent = "Idle. Click again."; });

      // Start the streaming session (low quality ~ 720p-ish)
      (async () => {
        try {
          const res = await avatar.createStartAvatar({
            avatarId: cfg.avatar_id,
            quality: "low",         // lower resolution/bitrate; faster start
            voice: { voice_id: cfg.voice_id }
          });
          sessionId = res.session_id;
        } catch (err) {
          console.error(err);
          statusEl.textContent = "Failed to start session. See console.";
        }
      })();

      // Send text to the SAME live session
      const sendLine = async (idx) => {
        try {
          await avatar.speak({
            sessionId,
            text: cfg.lines[idx],
            task_type: TaskType.REPEAT   // say exactly what we send
          });
        } catch (err) {
          console.error(err);
          statusEl.textContent = "Speak failed. See console.";
        }
      };
      btns[0].addEventListener('click', () => sendLine(0));
      btns[1].addEventListener('click', () => sendLine(1));
      btns[2].addEventListener('click', () => sendLine(2));
    </script>
  </body>
</html>
"""

components.html(html_template.replace("__CFG_JSON__", json.dumps(cfg)), height=560)
