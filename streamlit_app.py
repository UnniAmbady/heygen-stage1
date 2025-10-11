import time
import requests
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="HeyGen – Stage 1 (Public Voice)", page_icon="🎤", layout="centered")

OUT_MSG = "Hello, how are you? Please let me know how I can help you today."

HEYGEN_API_KEY = st.secrets["HeyGen"]["heygen_api_key"]

HEADERS = {"Authorization": f"Bearer {HEYGEN_API_KEY}", "Content-Type": "application/json"}
CREATE_VIDEO_URL = "https://api.heygen.com/v2/video/generate"
STATUS_URL = "https://api.heygen.com/v1/video_status.get"

st.title("🎤 HeyGen – Stage 1 (Proprietary Avatar + Public Voice)")
st.write("This version uses your avatar and the public voice **Mark**.")

avatar_id = st.text_input("Avatar ID", "a948e05bf0344480a397bef6a1452b9e")
voice_id = st.text_input("Voice ID ('Mark')", "f38a635bee7a4d1f9b0a654a31d050d2")

st.text_area("Script", OUT_MSG, height=80, disabled=True)

def create_video(avatar_id, voice_id, text):
    payload = {
        "title": "Stage 1 – Public Voice",
        "caption": False,
        "video_inputs": [{
            "character": {"type": "avatar", "avatar_id": avatar_id},
            "voice": {"type": "text", "voice_id": voice_id, "input_text": text},
            "background": {"type": "color", "value": "#ffffff"}
        }]
    }
    r = requests.post(CREATE_VIDEO_URL, headers=HEADERS, json=payload, timeout=60)
    r.raise_for_status()
    vid = r.json().get("video_id")
    if not vid:
        raise RuntimeError(f"No video_id returned: {r.text}")
    return vid

def poll_video(video_id, timeout_s=180):
    start = time.time()
    while time.time() - start < timeout_s:
        r = requests.get(STATUS_URL, headers=HEADERS, params={"video_id": video_id}, timeout=30)
        r.raise_for_status()
        data = r.json().get("data", {})
        if data.get("status") == "completed":
            return data.get("video_url")
        if data.get("status") == "failed":
            raise RuntimeError(f"Render failed: {data.get('error')}")
        time.sleep(1)
    raise TimeoutError("Video not ready yet.")

if st.button("Generate Video"):
    try:
        with st.spinner("Rendering avatar video…"):
            vid = create_video(avatar_id.strip(), voice_id.strip(), OUT_MSG)
            url = poll_video(vid)
        st.success("✅ Video Ready!")
        st.video(url)

        Path("logs").mkdir(exist_ok=True)
        with open("logs/outgoing.log", "a", encoding="utf-8") as f:
            f.write(f"[video_id={vid}] avatar_id={avatar_id} voice_id={voice_id} | text={OUT_MSG}\n")
    except Exception as e:
        st.error(f"Error: {e}")

st.caption("Note: Returned video URLs expire after a few days; poll the status endpoint again to refresh.")
