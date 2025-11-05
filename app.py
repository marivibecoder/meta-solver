# app.py
from flask import Flask, request, make_response
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from openai import OpenAI
import os

# === CONFIG ===
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# valida env vars al boot (opcional)
assert SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET and OPENAI_API_KEY, "Faltan env vars"

# === INIT ===
bolt_app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)
client_ai = OpenAI(api_key=OPENAI_API_KEY)

# --- Healthcheck
@flask_app.route("/", methods=["GET"])
def home():
    return "✅ Meta Solver online"

# --- Slack Events endpoint (incluye URL verification)
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.get_json(force=True, silent=True) or {}
    if "challenge" in data:
        return make_response(data["challenge"], 200, {"content_type": "text/plain"})
    return handler.handle(request)

# === EVENTOS ===
@bolt_app.event("message")
def handle_message_events(body, say, client, event):
    try:
        # ignorar mensajes del sistema/bots
        if event.get("subtype") == "bot_message":
            return

        user = event.get("user")
        channel = event.get("channel")
        text = event.get("text", "").strip()
        ts = event.get("ts")

        # 👀 reacción al mensaje original (no romper si no puede)
        try:
            client.reactions_add(channel=channel, timestamp=ts, name="eyes")
        except Exception as e:
            print("reactions_add error:", e)

        # 🧠 Prompt
        prompt = f"""
Sos Meta Solver, un asistente técnico del equipo de Darwin AI que ayuda a resolver problemas de Meta,
Meta Business Manager y WhatsApp Business API (número, conexión a API, co-existence, permisos, tokens, webhooks, etc.).

Leé el mensaje del usuario y respondé en español de forma clara, útil y empática.
Usá toda la información general/técnica que conozcas para resolver; cuando sea posible, agregá links oficiales o confiables.

Formato:
1) Diagnóstico en 1 línea.
2) Causas probables.
3) Pasos concretos (bullets cortos).
4) Link(s) útil(es).
5) Si falta info, pedila explícitamente.

Mensaje del usuario:
\"\"\"{text}\"\"\" 
"""

        # 🧠 Llamada al modelo (usa el SDK nuevo)
        completion = client_ai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = completion.choices[0].message.content.strip()

        # 🧵 responder en hilo
        say(text=response_text, thread_ts=ts)

    except Exception as e:
        print("💥 Error en handle_message_events:", e)
        try:
            say(thread_ts=event.get("ts"), text=f"⚠️ Error procesando el mensaje: {e}")
        except Exception:
            pass

# === MAIN (para correr local). En Railway usamos gunicorn.
if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
