import json
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="HeyGen — Realtime Avatar (Public)", page_icon="🎥", layout="centered")

API_KEY = st.secrets["HeyGen"]["heygen_api_key"]
HEYGEN_BASE = "https://api.heygen.com/v1"

# ---------- Helpers ----------

def fetch_interactive_avatars():
    """
    Return:
      avatars: list[dict] -> [{label, avatar_id, default_voice, is_public, status, normal_preview, created_at}]
      payload: dict        -> raw response body for diagnostics/interpretation
    """
    url = f"{HEYGEN_BASE}/streaming/avatar.list"
    r = requests.get(url, headers={"accept": "application/json", "X-Api-Key": API_KEY}, timeout=30)
    r.raise_for_status()
    payload = r.json() if r.headers.get("content-type","").startswith("application/json") else {"raw": r.text}
    data = payload.get("data") or []

    out = []
    for a in data:
        out.append({
            "label": a.get("pose_name") or a.get("avatar_id"),
            "avatar_id": a.get("avatar_id"),
            "default_voice": a.get("default_voice") or "",
            "is_public": bool(a.get("is_public")),
            "status": a.get("status"),
            "normal_preview": a.get("normal_preview"),
            "created_at": a.get("created_at"),
        })

    # de-dup by avatar_id while preserving order
    seen, deduped = set(), []
    for item in out:
        aid = item["avatar_id"]
        if not aid or aid in seen:
            continue
        seen.add(aid)
        deduped.append(item)
    return deduped, payload


def create_streaming_token() -> str:
    r = requests.post(
        f"{HEYGEN_BASE}/streaming.create_token",
        headers={"X-Api-Key": API_KEY, "Accept": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    token = (r.json().get("data") or {}).get("token")
    if not token:
        raise RuntimeError(f"No token in response: {r.text}")
    return token


def interpret_avatar_list(payload: dict, avatars: list[dict]) -> str:
    """
    Build a human-friendly interpretation of the /streaming/avatar.list response body.
    Shown with st.error(..., width="stretch") for visibility.
    """
    lines = []
    code = payload.get("code")
    lines.append(f"code: {code!r}")

    data = payload.get("data")
    if not isinstance(data, list):
        lines.append("data: <missing or not a list>")
        return "\n".join(lines)

    total = len(data)
    lines.append(f"data: list with {total} item(s)")

    # Status breakdown
    by_status = {}
    for a in data:
        s = a.get("status", "<none>")
        by_status[s] = by_status.get(s, 0) + 1
    status_summary = ", ".join([f"{k}: {v}" for k, v in by_status.items()])
    lines.append(f"status breakdown: {status_summary or '<none>'}")

    # Public vs. private
    pub = sum(1 for a in data if a.get("is_public"))
    prv = total - pub
    lines.append(f"public: {pub}, private: {prv}")

    # Fields health
    missing_avatar_id = sum(1 for a in data if not a.get("avatar_id"))
    missing_pose_name = sum(1 for a in data if not a.get("pose_name"))
    missing_default_voice = sum(1 for a in data if not a.get("default_voice"))
    lines.append(f"missing avatar_id: {missing_avatar_id}, pose_name: {missing_pose_name}, default_voice: {missing_default_voice}")

    # First ACTIVE item preview
    first_active = next((a for a in data if a.get("status") == "ACTIVE"), None)
    if first_active:
        lines.append("first ACTIVE item:")
        lines.append(f"  avatar_id: {first_active.get('avatar_id')}")
        lines.append(f"  pose_name: {first_active.get('pose_name')}")
        lines.append(f"  default_voice: {first_active.get('default_voice')}")
        lines.append(f"  is_public: {first_active.get('is_public')}")
        lines.append(f"  normal_preview: {first_active.get('normal_preview')}")
    else:
        lines.append("⚠️ no ACTIVE items found")

    # Compare raw->prepared list
    if avatars:
        lines.append(f"prepared dropdown options: {len(avatars)} (deduplicated by avatar_id)")
    else:
        lines.append("⚠️ prepared dropdown has no items (likely all missing avatar_id or filtered)")

    # Optional: echo first few raw objects (minified keys) for quick glance
    preview_count = min(3, total)
    if preview_count:
        lines.append("sample items (trimmed):")
        for i in range(preview_count):
            a = data[i]
            lines.append(
                f"  {i+1}. id={a.get('avatar_id')} • name={a.get('pose_name')} • default_voice={a.get('default_voice')} • status={a.get('status')} • public={a.get('is_public')}"
            )
    return "\n".join(lines)

# ---------- UI ----------

st.title("🎥 HeyGen Streaming Avatar — Interactive (Live)")
st.caption("Avatars are loaded via API. Voice auto-selected from each avatar’s default_voice. Includes response-body interpretation for debugging.")

# Load avatar list
with st.spinner("Loading available Interactive Avatars…"):
    avatars, raw_payload = fetch_interactive_avatars()

# NEW: Display interpretation of the Response Body as an alert panel
interp = interpret_avatar_list(raw_payload, avatars)
st.error(interp, icon="🧭", width="stretch")

if not avatars:
    st.stop()

labels = [a["label"] for a in avatars]
idx = 0
label = st.selectbox("Choose an Interactive Avatar:", labels, index=idx)
chosen = next(a for a in avatars if a["label"] == label)
avatar_id = chosen["avatar_id"]
voice_id = chosen["default_voice"] or "f38a635bee7a4d1f9b0a654a31d050d2"  # fallback

# Create token
token = create_streaming_token()
st.info(f"Token OK (len={len(token)}). Prefix: {token[:8]}…")
st.success(f"Using avatar: {label}  •  id: {avatar_id}  •  voice: {voice_id[:8]}…")

# Inject values into client
with open("client.html", "r", encoding="utf-8") as f:
    html = f.read()

html = (html
        .replace("__TOKEN__", token)
        .replace("__AVATAR_ID__", avatar_id)
        .replace("__VOICE_ID__", voice_id)
        .replace("__LINE1__", "Hello, how are you.")
        .replace("__LINE2__", "Welcome to our restaurant.")
        .replace("__LINE3__", "It is our pleasure serving you.")
)

components.html(html, height=820, scrolling=True)
