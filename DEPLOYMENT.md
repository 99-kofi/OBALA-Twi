# Deploying OBALA-Twi

## Important: Streamlit on Vercel

`app.py` is a **Streamlit** app. Vercel's serverless runtime is not a good fit for long-lived Streamlit sessions (websocket/session behavior), so full production Streamlit deployment on Vercel is unreliable.

## Recommended deployment (for this exact app)

Use **Streamlit Community Cloud**, **Render**, or **Railway** for `app.py`.

---

## If you still want Vercel

Use Vercel as a thin web layer and host Streamlit elsewhere:

1. Deploy this Streamlit app to Streamlit Community Cloud (or Render/Railway).
2. Create a small Vercel frontend (or redirect) that points users to the hosted Streamlit URL.
3. Keep your secrets (`GEMINI_API_KEY`) only in the Streamlit host environment.

---

## Vercel build error fix

If Vercel shows:

`Found app.py but it does not export a top-level "app", "application", or "handler" variable.`

this repository is being auto-detected as a Python serverless app. To avoid that, `vercel.json` now forces a **static-only** build from `public/**` and routes all paths to `public/index.html`.

## Quick setup (recommended path with Streamlit Community Cloud)

1. Push this repository to GitHub.
2. Go to Streamlit Community Cloud and create a new app.
3. Set:
   - **Main file path**: `app.py`
   - **Python dependencies**: from `requirements.txt`
4. Add secret:
   - `GEMINI_API_KEY=<your_key>`
5. Deploy.

---

## Environment variables required

- `GEMINI_API_KEY`

Without this variable, the app stops at startup.
