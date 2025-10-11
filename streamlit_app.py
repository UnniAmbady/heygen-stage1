import time
import requests
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="HeyGen — Stage 1", page_icon="🎤", layout="centered")

OUT_MSG = "Hello, how are you? Please let me know how I can help you today."

HEYGEN_API_KEY = st.secrets["HeyGen"]["heygen_api_key"]

HEADERS = {
    "X-Api-Key": HEYGEN_API_KEY,   # correct auth header
    "Accept": "application/json",
    "Content-Type": "application/json",
}

CREATE_VIDEO_URL = "https://api.heygen.com/v2/video/generate"   # POST
STATUS_URL       = "https://api.heygen.com/v1/video_status.get" # GET

st.title("🎤 HeyGen — Stage 1 (Proprietary Avatar + Public Voice)")
st.write("Speaks a fixed line with your avatar and the public voice **Mark**.")

avatar_id_default = "bf01e45ed0c04fe6958ca6551ce17ca0"      # your Avatar ID
group_id_info     = "a948e05bf0344480a397bef6a1452b9e"      # FYI
voice_id_default  = "f38a635bee7a4d1f9b0a654a31d050d2"      # public voice “Mark”

col1, col2 = st.columns(2)
with col1:
    avatar_id = st.text_input("Avatar ID", value=avatar_id_default)
with col2:
    voice_id = st.text_input("Voice ID (Mark)", value=voice_id_default)

st.caption(f"(FYI) Avatar Group ID on your account: {group_id_info}")
st.text_area("Script (Stage 1 fixed)", OUT_MSG, height=80, disabled=True)

def create_video(avatar_id: str, voice_id: str, text: str) -> str:
    payload = {
        "title": "Stage 1 — Public Voice",
        "caption": False,
        "video_inputs": [{
            "character": {"type": "avatar", "avatar_id": avatar_id},
            "voice": {"type": "text", "voice_id": voice_id, "input_text": text},
            "background": {"type": "color", "value": "#ffffff"}
        }]
    }
    r = requests.post(CREATE_VIDEO_URL, headers=HEADERS, json=payload, timeout=60)
    r.raise_for_status()
    resp = r.json()
    # <-- FIX: support both shapes, but HeyGen returns {"data":{"video_id":...}}
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
        status = data.get("status")
        if status == "completed":
            return data.get("video_url")
        if status == "failed":
            raise RuntimeError(f"Render failed: {data.get('error')}")
        time.sleep(1)
    raise TimeoutError("Video not ready yet. Try again shortly.")

if st.button("Generate Video"):
    try:
        vid = create_video(avatar_id.strip(), voice_id.strip(), OUT_MSG)
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
                f.write(f"[video_id={vid}] avatar_id={avatar_id} voice_id={voice_id} | text={OUT_MSG}\n")
        except Exception:
            pass

st.caption("Notes: Use X-Api-Key auth. /v2/video/generate is POST-only; opening it in a browser (GET) shows 405 by design. Returned video URLs are temporary.")
