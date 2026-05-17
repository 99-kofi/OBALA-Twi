import streamlit as st
import requests
import json
from gradio_client import Client, handle_file
import os
import logging
from PIL import Image
import tempfile
from streamlit_mic_recorder import mic_recorder
from dotenv import load_dotenv

# ---------------- ENV ----------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_NAME = "gemini-3-flash-preview"
TTS_MODEL = "Ghana-NLP/Southern-Ghana-TTS-Public"
STT_MODEL = "KhayaAI/Southern-Ghana-ASR-UI"

if not GEMINI_API_KEY:
    st.error("GEMINI_API_KEY not found in .env")
    st.stop()

logging.basicConfig(level=logging.INFO)

# ---------------- TWI ERRORS ----------------
TWI_ERRORS = {
    "GEMINI_API_FAILED": "Mepakyɛw, m'atwerɛ adwinnadeɛ no anyɛ adwuma yie.",
    "TRANSCRIPTION_FAILED": "Mepakyɛw, mantumi ante deɛ wokaeɛ no yie.",
    "AUDIO_GENERATION_FAILED": "Mepakyɛw, mantumi anyɛ nne adwumadiɛ no yie."
}

# ---------------- PAGE CONFIG ----------------
try:
    logo = Image.open("obpic.png")
    st.set_page_config(page_title="OBALA TWI", page_icon=logo, layout="wide")
except Exception:
    st.set_page_config(page_title="OBALA TWI", page_icon="🇬🇭", layout="wide")

# ---------------- STYLES ----------------
st.markdown(
    """
<style>
:root {
  --bg1: #f4ecff;
  --bg2: #fdf6ff;
  --glass: rgba(255, 255, 255, 0.35);
  --glass-strong: rgba(255, 255, 255, 0.55);
  --text: #251b3f;
  --accent: #8e72ff;
  --accent-2: #ff8cd7;
}

[data-testid="stAppViewContainer"] {
  background: radial-gradient(circle at top left, #f1e8ff 0%, #f8f0ff 40%, #fff7fd 100%);
}

.main .block-container {
  padding-top: 1.2rem;
  padding-bottom: 2rem;
  max-width: 900px;
}

.hero {
  border-radius: 28px;
  padding: 1.5rem;
  backdrop-filter: blur(14px);
  background: linear-gradient(140deg, rgba(255,255,255,.58), rgba(255,255,255,.28));
  border: 1px solid rgba(255,255,255,.55);
  box-shadow: 0 12px 35px rgba(120, 80, 200, 0.15);
  margin-bottom: 1rem;
}

.glass-card {
  border-radius: 24px;
  padding: 1rem;
  backdrop-filter: blur(14px);
  background: var(--glass);
  border: 1px solid rgba(255,255,255,.5);
  box-shadow: 0 10px 28px rgba(140, 100, 190, 0.12);
}

.orb {
  width: 74px;
  height: 74px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  box-shadow: 0 0 30px rgba(142, 114, 255, .45);
  display: inline-flex;
  justify-content: center;
  align-items: center;
  font-size: 1.9rem;
}

.small-chip {
  display: inline-block;
  border-radius: 999px;
  padding: 0.2rem 0.7rem;
  margin: 0.2rem 0.25rem 0 0;
  font-size: 0.78rem;
  color: #443762;
  background: rgba(255, 255, 255, 0.68);
  border: 1px solid rgba(255,255,255,.8);
}

.stButton>button {
  border-radius: 999px;
  border: 0;
  background: linear-gradient(120deg, var(--accent), var(--accent-2));
  color: white;
  font-weight: 600;
  padding: 0.35rem 1rem;
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------- CLIENTS ----------------
@st.cache_resource
def init_tts_client():
    return Client(TTS_MODEL)


@st.cache_resource
def init_stt_client():
    return Client(STT_MODEL)


tts_client = init_tts_client()
stt_client = init_stt_client()

# ---------------- MEMORY UTILS ----------------
MAX_TURNS = 8
RECENT_TURNS = 6

def summarize_history(messages):
    convo = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
    prompt = f"""
Bɔ nsɛnhyɛsoɔ tiawa wɔ Akan Twi mu fa kasa yi ho.
Fa nsɛnhyɛsoɔ titiriw nko ara, mmɔ mmɔden mmɔ akomam.
Kasa:
{convo}
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 200}
    }

    res = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload)
    )
    data = res.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]

# ---------------- SESSION STATE ----------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Afehyia pa! Me din de OBALA. Mɛtumi aboa wo sɛn?"}
    ]

if "view_mode" not in st.session_state:
    st.session_state.view_mode = "💬 Chat"

# ---------------- UI HEADER ----------------
st.markdown(
    """
<div class="hero">
  <div style="display:flex; gap:1rem; align-items:center;">
    <div class="orb">🤖</div>
    <div>
      <h2 style="margin:0; color:#291f42;">OBALA AI Sidekick</h2>
      <p style="margin:.35rem 0 0 0; color:#4e3f73;">Calm, emotional, and voice-first Twi assistant.</p>
    </div>
  </div>
  <div style="margin-top:.65rem;">
    <span class="small-chip">Glassmorphism</span>
    <span class="small-chip">Voice-first</span>
    <span class="small-chip">Productivity + Chat</span>
    <span class="small-chip">Multimodal AI</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.session_state.view_mode = st.segmented_control(
    "Screen",
    options=["👋 Welcome", "📊 Dashboard", "💬 Chat"],
    default=st.session_state.view_mode,
)

if st.session_state.view_mode == "👋 Welcome":
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("Meet OBALA")
    st.write("A digital companion designed to feel warm, intelligent, and always available.")
    st.write("Use voice or text to start a gentle Akan Twi conversation.")
    st.button("🎙️ Start Voice Session")
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.view_mode == "📊 Dashboard":
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("Good day 👋")
    st.caption("Smart integrations and quick actions")
    c1, c2 = st.columns(2)
    with c1:
        st.info("📆 Calendar\n\nNo meetings in the next 2 hours")
        st.info("💬 Slack\n\n3 unread mentions need responses")
    with c2:
        st.info("🧠 Prompt Idea\n\n'Boa me ma menhyehyɛ me nnawɔtwe adwuma.'")
        st.info("🎯 Quick Action\n\nCreate Twi summary from today notes")
    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.caption("Kyerɛw anaa kasa — Twi anaa Borɔfo.")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("audio") and os.path.isfile(msg["audio"]):
                st.audio(msg["audio"])

    audio_info = mic_recorder("🎤 Kasa", "⏹️ Gyae", just_once=True)
    text_prompt = st.chat_input("Kyerɛw wo asɛm...")

    if audio_info and audio_info["bytes"]:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
                f.write(audio_info["bytes"])
                path = f.name

            result = stt_client.predict(
                audio=handle_file(path),
                LANG="Asante Twi",
                api_name="/predict"
            )
            os.remove(path)

            if result.strip():
                st.session_state.messages.append({"role": "user", "content": result.strip()})
                st.rerun()

        except Exception:
            st.error(TWI_ERRORS["TRANSCRIPTION_FAILED"])

    if text_prompt:
        st.session_state.messages.append({"role": "user", "content": text_prompt})
        st.rerun()

    if st.session_state.messages[-1]["role"] == "user":
        if len(st.session_state.messages) > MAX_TURNS:
            summary = summarize_history(st.session_state.messages[:-4])
            st.session_state.messages = (
                [{"role": "assistant", "content": f"Nsɛnhyɛsoɔ: {summary}"}]
                + st.session_state.messages[-4:]
            )

        with st.chat_message("assistant"):
            with st.spinner("OBALA redwene ho..."):
                system_prompt = """
Wo ne OBALA wɔ WAIT Technologies.
Wo kasa titiriw ne Akan Twi.
Bua bere nyinaa wɔ Akan Twi mu.
Sɛ w’asɛm tenten dodo a, wie no yie na twetwew twetwew, na twɛn “toa so”.
Ntwetwe nsɛm mfinimfini.
Sɛ wunnim a, ka “Mepa wo kyɛw, mennim”.
"""

                recent = st.session_state.messages[-RECENT_TURNS:]

                contents = [
                    {
                        "role": "model" if m["role"] == "assistant" else "user",
                        "parts": [{"text": m["content"]}]
                    }
                    for m in recent
                ]

                payload = {
                    "contents": contents,
                    "system_instruction": {"parts": [{"text": system_prompt}]},
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": 900
                    }
                }

                try:
                    res = requests.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}",
                        headers={"Content-Type": "application/json"},
                        data=json.dumps(payload)
                    )
                    data = res.json()

                    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    text_reply = "".join(p.get("text", "") for p in parts).strip()

                    if not text_reply:
                        text_reply = TWI_ERRORS["GEMINI_API_FAILED"]

                except Exception:
                    text_reply = TWI_ERRORS["GEMINI_API_FAILED"]

                st.markdown(text_reply)

            audio_path = None
            try:
                audio_result = tts_client.predict(
                    text=text_reply,
                    lang="Asante Twi",
                    speaker="Male (Low)",
                    api_name="/predict"
                )
                if isinstance(audio_result, str) and os.path.isfile(audio_result):
                    st.audio(audio_result)
                    audio_path = audio_result
            except Exception:
                st.warning(TWI_ERRORS["AUDIO_GENERATION_FAILED"])

            st.session_state.messages.append(
                {"role": "assistant", "content": text_reply, "audio": audio_path}
            )
            st.rerun()
