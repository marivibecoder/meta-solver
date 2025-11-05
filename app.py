from flask import Flask, request, make_response
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
import openai
import os
import json

# === CONFIGURACIÓN ===
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# === INICIALIZACIÓN ===
bolt_app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)

openai.api_key = OPENAI_API_KEY


# === RUTAS FLASK ===
@flask_app.route("/", methods=["GET"])
def home():
    return "✅ Meta Solver online"


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.get_json()
    print("📩 Incoming Slack event:", data)

    # URL Verification
    if data and "challenge" in data:
        return make_response(data["challenge"], 200, {"content_type": "text/plain"})

    return handler.handle(request)


# === EVENTOS SLACK ===
@bolt_app.event("message")
def handle_message_events(body, say, client, event):
    try:
        # Ignorar mensajes del bot mismo
        if event.get("subtype") == "bot_message":
            return

        user = event.get("user")
        channel = event.get("channel")
        text = event.get("text")
        ts = event.get("ts")

        # 👀 Reaccionar al mensaje original
        client.reactions_add(
            channel=channel,
            timestamp=ts,
            name="eyes"
        )

        # 🧠 Generar respuesta con OpenAI
        prompt = f"Un usuario escribió: '{text}'. Respondé con una breve sugerencia o ayuda profesional."
        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = completion.choices[0].message.content.strip()

        # 💬 Responder en hilo
        say(
            text=response_text,
            thread_ts=ts
        )

    except Exception as e:
        print("💥 Error en handle_message_events:", e)
        say(thread_ts=event["ts"], text=f"⚠️ Error procesando el mensaje: {e}")


# === MAIN ===
if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
