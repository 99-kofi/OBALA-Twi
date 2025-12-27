# obala_twi_app.py
# Streamlit-based OBALA TWI chat with Gemini + STT + TTS
# FIXED: conversation cutoffs, memory overflow, truncation

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

MODEL_NAME = "gemini-1.5-flash-preview"
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
    st.set_page_config(page_title="OBALA TWI", page_icon=logo)
except:
    st.set_page_config(page_title="OBALA TWI", page_icon="🇬🇭")

# ---------------- STYLES ----------------
st.markdown("""
<style>
.stButton>button {
    padding: 0.25rem 0.75rem;
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)

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

# ---------------- UI HEADER ----------------
st.title("🇬🇭 OBALA")
st.caption("Your Akan (Twi) AI Assistant")
st.info("Kyerɛw anaa kasa — Twi anaa Borɔfo.")

# ---------------- DISPLAY CHAT ----------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("audio") and os.path.isfile(msg["audio"]):
            st.audio(msg["audio"])

# ---------------- INPUT ----------------
audio_info = mic_recorder("🎤 Kasa", "⏹️ Gyae", just_once=True)
text_prompt = st.chat_input("Kyerɛw wo asɛm...")

# ---------------- STT ----------------
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
            st.session_state.messages.append(
                {"role": "user", "content": result.strip()}
            )
            st.rerun()

    except Exception:
        st.error(TWI_ERRORS["TRANSCRIPTION_FAILED"])

# ---------------- TEXT INPUT ----------------
if text_prompt:
    st.session_state.messages.append(
        {"role": "user", "content": text_prompt}
    )
    st.rerun()

# ---------------- AI RESPONSE ----------------
if st.session_state.messages[-1]["role"] == "user":

    # Summarize if history too long
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

                parts = data.get("candidates", [{}])[0] \
                            .get("content", {}) \
                            .get("parts", [])

                text_reply = "".join(p.get("text", "") for p in parts).strip()

                if not text_reply:
                    text_reply = TWI_ERRORS["GEMINI_API_FAILED"]

            except Exception:
                text_reply = TWI_ERRORS["GEMINI_API_FAILED"]

            st.markdown(text_reply)

        # ---------------- TTS ----------------
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
