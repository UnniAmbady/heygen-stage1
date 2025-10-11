import json
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="HeyGen — Realtime Avatar Demo", page_icon="🎥", layout="centered")

# ---- Fixed IDs (as requested) ----
AVATAR_ID = "bf01e45ed0c04fe6958ca6551ce17ca0"
VOICE_ID  = "f38a635bee7a4d1f9b0a654a31d050d2"  # Public "Mark"

# ---- Secrets ----
HEYGEN_API_KEY = st.secrets["HeyGen"]["heygen_api_key"]

# ---- Create a streaming SESSION TOKEN (required by SDK; not your API key) ----
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

# Generate one token per page load (simple demo)
session_token = create_session_token()

st.title("🎥 HeyGen Streaming Avatar — quick proof")
st.caption("One live avatar stream at low/720p quality; click a button to make it speak in real time.")

# ---- Embed a small HTML/JS client that uses the Streaming Avatar SDK ----
# We pass config via a JSON script tag to avoid string escaping headaches.
cfg = {
    "token": session_token,
    "avatar_id": AVATAR_ID,
    "voice_id": VOICE_ID,
    # three short lines you wanted (they are only sent when you click)
    "lines": [
        "Hello, how are you.",
        "Welcome to our restaurant.",
        "It is our pleasure serving you."
    ]
}

components.html(f"""
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <style>
      body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; }}
      #wrap {{ display: grid; gap: 12px; max-width: 840px; margin: 0 auto; }}
      video {{ width: 100%; aspect-ratio: 16/9; background: #000; border-radius: 12px; }}
      .row {{ display: grid; gap: 8px; grid-template-columns: repeat(3, 1fr); }}
      button {{ padding: 10px 12px; border-radius: 10px; border: 1px solid #ddd; cursor: pointer; }}
      button:disabled {{ opacity: 0.5; cursor: not-allowed; }}
      .muted {{ font-size: 12px; color: #666; }}
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

    <!-- Pass config from Streamlit -->
    <script id="cfg" type="application/json">{json.dumps(cfg)}</script>

    <!-- Load the Streaming Avatar SDK as an ES module from jsDelivr -->
    <script type="module">
      import {{ StreamingAvatar, TaskType, StreamingEvents }} from "https://cdn.jsdelivr.net/npm/@heygen/streaming-avatar/+esm";

      const cfg = JSON.parse(document.getElementById('cfg').textContent);
      const videoEl = document.getElementById('avatarVideo');
      const statusEl = document.getElementById('status');
      const btns = [document.getElementById('btn1'), document.getElementById('btn2'), document.getElementById('btn3')];

      // Create SDK client with the per-session token
      const avatar = new StreamingAvatar({ token: cfg.token });

      let sessionId = null;

      // When the media stream is ready, attach it to the <video>
      avatar.on(StreamingEvents.STREAM_READY, (evt) => {{
        const stream = evt.detail;
        videoEl.srcObject = stream;
        videoEl.muted = false;    // unmute so you can hear it
        statusEl.textContent = "Avatar is live. Click a button to speak.";
        btns.forEach(b => b.disabled = false);
      }});

      avatar.on(StreamingEvents.AVATAR_START_TALKING, () => {{
        statusEl.textContent = "Speaking…";
      }});
      avatar.on(StreamingEvents.AVATAR_STOP_TALKING, () => {{
        statusEl.textContent = "Idle. Click a button to speak again.";
      }});

      // Start the streaming session immediately
      (async () => {{
        try {{
          const startRes = await avatar.createStartAvatar({{
            // Use your specific avatar and voice; set lower quality for quicker/720p-ish streaming
            avatarId: cfg.avatar_id,
            quality: "low",                          // <= lower resolution/bitrate
            voice: {{ voice_id: cfg.voice_id }}
          }});
          sessionId = startRes.session_id;
        }} catch (err) {{
          console.error(err);
          statusEl.textContent = "Failed to start avatar session. Check console.";
        }}
      }})();

      // Wire buttons to send short texts to the SAME live session
      const sendLine = async (idx) => {{
        try {{
          await avatar.speak({{
            sessionId,
            text: cfg.lines[idx],
            task_type: TaskType.REPEAT       // speak exactly the provided text
          }});
        }} catch (err) {{
          console.error(err);
          statusEl.textContent = "Speak failed. See console.";
        }}
      }};
      btns[0].addEventListener('click', () => sendLine(0));
      btns[1].addEventListener('click', () => sendLine(1));
      btns[2].addEventListener('click', () => sendLine(2));
    </script>
  </body>
</html>
""", height=560)
