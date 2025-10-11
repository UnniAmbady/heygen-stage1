import time
import requests
import streamlit as st

st.set_page_config(page_title="HeyGen Stage 1 — Avatar speaks", page_icon="🎤", layout="centered")

# ----- CONFIG -----
# Hard-coded message (Stage 1)
OUT_MSG = "Hello, how are you? Please let me know how I can help you today."

# Read API key from Streamlit Secrets
HEYGEN_API_KEY = st.secrets["HeyGen"]["heygen_api_key"]

# Base endpoints (per HeyGen docs)
LIST_AVATARS_URL = "https://api.heygen.com/v2/avatars"          # list standard avatars  :contentReference[oaicite:0]{index=0}
LIST_VOICES_URL  = "https://api.heygen.com/v2/voices"            # list voices           :contentReference[oaicite:1]{index=1}
CREATE_VIDEO_URL = "https://api.heygen.com/v2/video/generate"    # create avatar video   :contentReference[oaicite:2]{index=2}
STATUS_URL       = "https://api.heygen.com/v1/video_status.get"  # poll video status     :contentReference[oaicite:3]{index=3}

HEADERS = {"Authorization": f"Bearer {HEYGEN_API_KEY}", "Content-Type": "application/json"}

st.title("🎤 HeyGen Avatar — Stage 1")
st.write("This demo picks a standard HeyGen avatar & voice, then speaks a hard-coded line.")

# ----- Fetch choices (avatars & voices) -----
@st.cache_data(ttl=300)
def fetch_avatars():
    r = requests.get(LIST_AVATARS_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    # Prefer non-premium avatars if available
    avatars = data.get("avatars", [])
    avatars_sorted = sorted(avatars, key=lambda a: (a.get("premium", False), a.get("avatar_name","")))
    return avatars_sorted

@st.cache_data(ttl=300)
def fetch_voices():
    r = requests.get(LIST_VOICES_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json().get("voices", [])

avatars = fetch_avatars()
voices  = fetch_voices()

if not avatars:
    st.error("No avatars found on your account. Open HeyGen and make sure you have access to standard avatars.")
    st.stop()

if not voices:
    st.error("No voices found on your account.")
    st.stop()

# Simple pickers
avatar_labels = [f'{a.get("avatar_name","(unnamed)")} — {a.get("avatar_id")}' + (" (premium)" if a.get("premium") else "") for a in avatars]
avatar_choice = st.selectbox("Choose an avatar", avatar_labels, index=0)
avatar_id = avatars[avatar_labels.index(avatar_choice)]["avatar_id"]

voice_labels = [f'{v.get("name","(unnamed)")} — {v.get("language","")} — {v.get("voice_id")}' for v in voices]
voice_choice = st.selectbox("Choose a voice", voice_labels, index=0)
voice_id = voices[voice_labels.index(voice_choice)]["voice_id"]

st.text_area("Script to speak (Stage 1 keeps this hard-coded)", OUT_MSG, height=80, disabled=True)

if st.button("Generate video"):
    with st.spinner("Requesting HeyGen to render the avatar video..."):
        payload = {
            "title": "Stage 1 Demo",
            "caption": False,
            "video_inputs": [
                {
                    # Character: standard studio avatar
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id
                    },
                    # Voice: speak text
                    "voice": {
                        "type": "text",
                        "voice_id": voice_id,
                        "input_text": OUT_MSG
                    },
                    # Optional plain background so the focus is the avatar
                    "background": {
                        "type": "color",
                        "value": "#ffffff"
                    }
                }
            ]
        }

        create = requests.post(CREATE_VIDEO_URL, headers=HEADERS, json=payload, timeout=60)
        if create.status_code >= 400:
            st.error(f"Create failed ({create.status_code}): {create.text}")
            st.stop()

        video_id = create.json().get("video_id")
        if not video_id:
            st.error("No video_id returned from HeyGen.")
            st.stop()

        # Poll status until 'completed'
        # (HeyGen status endpoint returns video_url when completed; URL expires after 7 days)
        #  :contentReference[oaicite:4]{index=4}
        status = None
        video_url = None
        for _ in range(120):  # up to ~2 minutes with 1s steps
            time.sleep(1)
            r = requests.get(STATUS_URL, headers=HEADERS, params={"video_id": video_id}, timeout=30)
            if r.status_code >= 400:
                st.error(f"Status check failed ({r.status_code}): {r.text}")
                st.stop()
            data = r.json().get("data", {})
            status = data.get("status")
            if status == "completed":
                video_url = data.get("video_url")
                break
            elif status == "failed":
                st.error(f"Render failed: {data.get('error')}")
                st.stop()
            # otherwise: waiting/processing/pending — keep polling

        if not video_url:
            st.warning(f"Video not ready yet (status: {status}). Try again.")
            st.stop()

        # Display the result
        st.success("Done! Here is your video:")
        st.video(video_url)

        # (Optional) log locally that we produced OUT_MSG
        try:
            from pathlib import Path
            logdir = Path("logs")
            logdir.mkdir(exist_ok=True)
            with open(logdir / "outgoing.log", "a", encoding="utf-8") as f:
                f.write(f"[video_id={video_id}] {OUT_MSG}\n")
        except Exception:
            pass

st.caption("Tip: The video URL returned by the status endpoint expires in ~7 days; poll the status endpoint again to refresh it.")
