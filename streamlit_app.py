import json
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="HeyGen — Realtime Avatar Demo", page_icon="🎥", layout="centered")

# ----- Fixed IDs (working ones) -----
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

session_token = create_session_token()

st.title("🎥 HeyGen Streaming Avatar — Live Proof")
st.caption("One live session. Click a button to speak. No rendering, no emails.")

# Only the browser needs this data
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

# IMPORTANT: not an f-string; no .format() anywhere.
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

    <!-- Config injected from Streamlit -->
    <script id="cfg" type="application/json">__CFG_JSON__</script>

    <!-- Streaming Avatar SDK -->
    <script type="module">
      import { StreamingAvatar, TaskType, StreamingEvents } from "https://cdn.jsdelivr.net/npm/@heygen/streaming-avatar/+esm";

      const cfg = JSON.parse(document.getElementById('cfg').textContent);
      const videoEl = document.getElementById('avatarVideo');
      const statusEl = document.getElementById('status');
      const unmuteBtn = document.getElementById('unmuteBtn');
      const btns = [document.getElementById('btn1'), document.getElementById('btn2'), document.getElementById('btn3')];

      // Create SDK client with the per-session token (not your API key)
      const avatar = new StreamingAvatar({ token: cfg.token });
      let sessionId = null;

      // Unmute after user interaction (autoplay policy)
      unmuteBtn.addEventListener('click', async () => {
        try {
          videoEl.muted = false;
          await videoEl.play();
          unmuteBtn.disabled = true;
          unmuteBtn.textContent = "Audio unmuted";
        } catch (e) {
          console.warn("Autoplay unblock failed:", e);
        }
      });

      avatar.on(StreamingEvents.STREAM_READY, (evt) => {
        videoEl.srcObject = evt.detail;
        statusEl.textContent = "Avatar is live. Click a button to speak.";
        btns.forEach(b => b.disabled = false);
      });

      avatar.on(StreamingEvents.AVATAR_START_TALKING, () => { statusEl.textContent = "Speaking…"; });
      avatar.on(StreamingEvents.AVATAR_STOP_TALKING, () => { statusEl.textContent = "Idle. Click again."; });

      // Start a low-quality (~720p) session for faster start
      (async () => {
        try {
          const res = await avatar.createStartAvatar({
            avatarId: cfg.avatar_id,
            quality: "low",             // lower bitrate/resolution for speed
            voice: { voice_id: cfg.voice_id }
          });
          sessionId = res.session_id;
        } catch (err) {
          console.error(err);
          statusEl.textContent = "Failed to start session. Open browser console for details.";
        }
      })();

      // Send text to the SAME live session
      const sendLine = async (idx) => {
        try {
          await avatar.speak({
            sessionId,
            text: cfg.lines[idx],
            task_type: TaskType.REPEAT
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

# Inject config JSON safely (no f-strings, no .format)
components.html(
    html_template.replace("__CFG_JSON__", json.dumps(cfg)),
    height=600
)
