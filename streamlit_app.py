import time
import requests
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="HeyGen — Stage 1 (Proprietary Avatar)", page_icon="🎤", layout="centered")

# ====== CONFIG (Stage 1) ======
OUT_MSG = "Hello, how are you? Please let me know how I can help you today."

# Read API key from Streamlit secrets
HEYGEN_API_KEY = st.secrets["HeyGen"]["heygen_api_key"]

HEADERS = {
    "Authorization": f"Bearer {HEYGEN_API_KEY}",
    "Content-Type": "application/json",
}

# Endpoints (per HeyGen docs)
LIST_VOICES_URL  = "https://api.heygen.com/v2/voices"
CREATE_VIDEO_URL = "https://api.heygen.com/v2/video/generate"
STATUS_URL       = "https://api.heygen.com/v1/video_status.get"

st.title("🎤 HeyGen — Stage 1 (Your Proprietary Avatar)")
st.write("This app uses **your own avatar** by ID and speaks a fixed line (Stage 1).")

# Pre-fill with your GroupID (you can change it if needed)
avatar_id = st.text_input(
    "Avatar ID (your proprietary avatar’s ID / group ID)",
    value="a948e05bf0344480a397bef6a1452b9e",  # from your message
)

# ---- Fetch voices (works even if you have no public avatars) ----
@st.cache_data(ttl=300)
def fetch_voices():
    r = requests.get(LIST_VOICES_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("voices", [])

voices = []
try:
    voices = fetch_voices()
except Exception as e:
    st.error(f"Failed to fetch voices: {e}")

if not voices:
    st.error("No voices available on your account. Please check your HeyGen plan/access.")
    st.stop()

voice_labels = [f'{v.get("name","(unnamed)")} — {v.get("language","")} — {v.get("voice_id")}' for v in voices]
voice_choice = st.selectbox("Choose a voice", voice_labels, index=0)
voice_id = voices[voice_labels.index(voice_choice)]["voice_id"]

st.text_area("Script (fixed for Stage 1)", OUT_MSG, height=90, disabled=True)

if st.button("Generate video"):
    if not avatar_id.strip():
        st.warning("Please enter a valid Avatar ID.")
        st.stop()

    with st.spinner("Requesting HeyGen to render the avatar video..."):
        payload = {
            "title": "Stage 1 — Proprietary Avatar",
            "caption": False,
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        # For proprietary avatars, pass your avatar’s ID here.
                        # (In many accounts this is the same UUID shown as Group ID.)
                        "avatar_id": avatar_id.strip()
                    },
                    "voice": {
                        "type": "text",
                        "voice_id": voice_id,
                        "input_text": OUT_MSG
                    },
                    "background": {"type": "color", "value": "#ffffff"}
                }
            ]
        }

        try:
            create = requests.post(CREATE_VIDEO_URL, headers=HEADERS, json=payload, timeout=60)
            create.raise_for_status()
        except requests.HTTPError as e:
            st.error(f"Create failed: {e.response.status_code} — {e.response.text}")
            st.stop()
        except Exception as e:
            st.error(f"Create failed: {e}")
            st.stop()

        video_id = create.json().get("video_id")
        if not video_id:
            st.error("No video_id returned by HeyGen.")
            st.stop()

        # Poll status until 'completed'
        video_url = None
        status = None
        for _ in range(180):  # up to ~3 minutes
            time.sleep(1)
            try:
                r = requests.get(STATUS_URL, headers=HEADERS, params={"video_id": video_id}, timeout=30)
                r.raise_for_status()
            except Exception as e:
                st.error(f"Status check failed: {e}")
                st.stop()

            data = r.json().get("data", {})
            status = data.get("status")
            if status == "completed":
                video_url = data.get("video_url")
                break
            if status == "failed":
                st.error(f"Render failed: {data.get('error')}")
                st.stop()

        if not video_url:
            st.warning(f"Video not ready yet (status: {status}). Please try again.")
            st.stop()

        # Show video
        st.success("Done! Here is your video:")
        st.video(video_url)

        # Simple local log
        try:
            Path("logs").mkdir(exist_ok=True)
            with open("logs/outgoing.log", "a", encoding="utf-8") as f:
                f.write(f"[video_id={video_id}] avatar_id={avatar_id} | text={OUT_MSG}\n")
        except Exception:
            pass

st.caption("Note: The returned video URL expires after a short time; recheck status with the same video_id to refresh.")
