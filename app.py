
# obala_twi_app.py
# Streamlit-based OBALA TWI chat with Gemini and Text-to-Speech output (Twi Error Messages)
# NOTE: This file contains a HARDCODED API KEY PLACEHOLDER for demo purposes.
# For production, store the key in an environment variable instead.

import streamlit as st
import requests
import json
from gradio_client import Client
import os
import logging

# --- Configuration ---
GEMINI_API_KEY = "AIzaSyDpAmrLDJjDTKi7TD-IS3vqQlBAYVrUbv4" # <-- IMPORTANT: REPLACE THIS
MODEL_NAME = "gemini-2.0-flash"
TTS_MODEL = "Ghana-NLP/Southern-Ghana-TTS-Public"

# Configure logging to show technical errors in the console (for the developer)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Twi Error Messages for the User ---
TWI_ERRORS = {
    "TTS_CONNECTION_FAILED": "Mepakyɛw, me nsa nka kasa adwinnadeɛ no mprempren. Bɔ mmɔden bio akyire yi.",
    "GEMINI_API_FAILED": "Mepakyɛw, m'atwerɛ adwinnadeɛ no anyɛ adwuma yie. Bɔ mmɔden bio.",
    "AUDIO_GENERATION_FAILED": "Mepakyɛw, asɛm ato me wɔ ɛnne no a mɛpagya mu. Mantumi anyɛ no yie.",
    "INVALID_AUDIO_PATH": "Kasa adwinnadeɛ no de biribi a ɛnsɛ amena me. Mantumi annye ɛnne no.",
    "AUDIO_PATH_NOT_FOUND": "Me nsa kaa kwan no deɛ, nanso ɛnne no nni hɔ. Mepakyɛw.",
}

# --- Main App ---

st.set_page_config(page_title="OBALA TWI", page_icon="🇬🇭", layout="centered")
st.title("🇬🇭 OBALA TWI — Akan Twi AI Assistant")
#st.caption(f"Powered by {MODEL_NAME} & {TTS_MODEL}")
st.caption("From WAIT ❤")

# --- Helper Functions ---
@st.cache_resource
def init_tts_client():
    """Initializes the Gradio client, with Twi error handling."""
    try:
        return Client(TTS_MODEL)
    except Exception as e:
        logging.error(f"Could not connect to the Text-to-Speech model: {e}")
        st.error(TWI_ERRORS["TTS_CONNECTION_FAILED"])
        return None

# --- App Initialization ---
tts_client = init_tts_client()
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Afehyia pa! Me din de OBALA. Mɛtumi aboa wo sɛn?"}
    ]

# --- Display Chat History ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "audio" in msg and msg["audio"]:
            if isinstance(msg["audio"], str) and os.path.isfile(msg["audio"]):
                st.audio(msg["audio"])

# --- Handle New User Input ---
if prompt := st.chat_input("Kyerɛw wo asɛm wɔ Twi mu..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # --- Generate and Display AI Response ---
    with st.chat_message("assistant"):
        # 1. Get text response from Gemini
        with st.spinner("OBALA redwene ho..."):
            text_reply = ""
            try:
                system_prompt = "You are OBALA, a friendly AI assistant developed by WAIT mfiridwuma ho nimdeɛ. Always and exclusively reply in the Akan Twi language of Ghana. Be concise. If you do not know the answer, say 'Mepa wo kyɛw, mennim'.Also emulate users conversation"
                gemini_messages = [{"role": ("model" if m["role"] == "assistant" else "user"), "parts": [{"text": m["content"]}]} for m in st.session_state.messages]
                payload = {"contents": gemini_messages, "system_instruction": {"parts": [{"text": system_prompt}]}, "generationConfig": {"temperature": 0.4, "maxOutputTokens": 400}}
                api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
                res = requests.post(api_url, headers={"Content-Type": "application/json"}, data=json.dumps(payload))
                res.raise_for_status()
                data = res.json()
                text_reply = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", TWI_ERRORS["GEMINI_API_FAILED"])
            except Exception as e:
                logging.error(f"Gemini API call failed: {e}")
                text_reply = TWI_ERRORS["GEMINI_API_FAILED"]
                st.error(text_reply)
        
        if text_reply and text_reply != TWI_ERRORS["GEMINI_API_FAILED"]:
             st.markdown(text_reply)
        
        # 2. Generate audio for the new response
        audio_path_to_store = None
        if text_reply and tts_client and text_reply != TWI_ERRORS["GEMINI_API_FAILED"]:
            with st.spinner("OBALA rekasa..."):
                audio_result = None
                try:
                    filepath_str = None
                    audio_result = tts_client.predict(text=text_reply, lang="Asante Twi", speaker="Male (High)", api_name="/predict")
                    
                    if isinstance(audio_result, str):
                        filepath_str = audio_result
                    elif isinstance(audio_result, dict) and 'name' in audio_result and isinstance(audio_result['name'], str):
                        filepath_str = audio_result['name']
                    
                    if filepath_str:
                        if os.path.isfile(filepath_str):
                            st.audio(filepath_str)
                            audio_path_to_store = filepath_str # Success!
                        else:
                            logging.warning(f"Audio generation failed: Path is not a valid file -> '{filepath_str}'")
                            st.warning(TWI_ERRORS["AUDIO_PATH_NOT_FOUND"])
                    else:
                        logging.warning(f"Audio generation failed: Could not extract filepath from TTS response. Received: {audio_result}")
                        st.warning(TWI_ERRORS["INVALID_AUDIO_PATH"])

                except Exception as e:
                    logging.error(f"An error occurred during audio generation: {e}")
                    logging.error(f"The raw data from TTS that caused the error was: {audio_result}")
                    st.error(TWI_ERRORS["AUDIO_GENERATION_FAILED"])

        # 3. Add the complete AI response to history
        st.session_state.messages.append({"role": "assistant", "content": text_reply, "audio": audio_path_to_store})
