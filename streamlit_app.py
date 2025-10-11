import time
import requests
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="HeyGen — Stage 1", page_icon="🎤", layout="centered")

OUT_MSG = "Hello, how are you? Please let me know how I can help you today."

HEYGEN_API_KEY = st.secrets["HeyGen"]["heygen_api_key"]
HEADERS = {"X-Api-Key": HEYGEN_API_KEY, "Accept": "application/json", "Content-Type": "application/json"}

CREATE_VIDEO_URL = "https://api.heygen.com/v2/video/generate"
STATUS_URL       = "https://api.heygen.com/v1/video_status.get"

st.title("🎤 HeyGen — Stage 1 (Avatar + Public Voice)")
avatar_id = st.text_input("Avatar ID", "bf01e45ed0c04fe6958ca6551ce17ca0")
voice_id  = st.text_input("Voice ID (Mark)", "f38a635bee7a4d1f9b0a654a31d050d2")

# Pick resolution; default to 720p to avoid plan errors
res = st.selectbox("Resolution", ["1280x720 (720p)", "1920x1080 (1080p)"], index=0)
width, height = (1280, 720) if res.startswith("1280") else (1920, 1080)

st.text_area("Script (fixed for Stage 1)", OUT_MSG, height=80, disabled=True)

def create_video(avatar_id: str, voice_id: str, text: str, width: int, height: int) -> str:
    payload = {
        "title": "Stage 1 — Public Voice",
        "caption": False,
        "dimension": {"width": width, "height": height},  # <-- explicit resolution
        "video_inputs": [{
            "character": {"type": "avatar", "avatar_id": avatar_id},
            "voice": {"type": "text", "voice_id": voice_id, "input_text": text},
            "background": {"type": "color", "value": "#ffffff"}
        }]
    }
    r = requests.post(CREATE_VIDEO_URL, headers=HEADERS, json=payload, timeout=60)
    r.raise_for_status()
    resp = r.json()
    vid = resp.get("video_id") or (resp.get("data") or {}).get("video_id")
    if not vid:
        raise RuntimeError(f"No video_id in response: {resp}")
    return vid

def poll_video(video_id: str, timeout_s: int = 240) -> str:
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
    raise TimeoutError("Video not ready yet. Try again shortly.")

if st.button("Generate Video"):
    try:
        vid = create_video(avatar_id.strip(), voice_id.strip(), OUT_MSG, width, height)
        url = poll_video(vid)
    except requests.HTTPError as e:
        st.error(f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        st.error(f"Error: {e}")
    else:
        st.success("✅ Video Ready!")
        st.video(url)
        try:
            Path("logs").mkdir(exist_ok=True)
            with open("logs/outgoing.log", "a", encoding="utf-8") as f:
                f.write(f"[video_id={vid}] {width}x{height} avatar_id={avatar_id} voice_id={voice_id} | {OUT_MSG}\n")
        except Exception:
            pass

st.caption("Note: If your plan is limited, stick to 720p. The video URL from status is temporary.")
