from flask import Flask, request, make_response
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
import openai
import os
import json
import requests

# === CONFIGURACIÓN ===
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

print("🔧 Starting app with:")
print("SLACK_BOT_TOKEN:", bool(SLACK_BOT_TOKEN))
print("SLACK_SIGNING_SECRET:", bool(SLACK_SIGNING_SECRET))

# === INICIALIZACIÓN ===
bolt_app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
openai.api_key = OPENAI_API_KEY
flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)


@flask_app.route("/", methods=["GET"])
def home():
    return "✅ Meta Solver online"


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    try:
        data = request.get_json(force=True)
        print("📩 Received from Slack:", data)

        # Slack URL Verification (Challenge)
        if data and "challenge" in data:
            challenge = data.get("challenge")
            print("✅ Returning challenge:", challenge)
            return make_response(challenge, 200, {"content_type": "text/plain"})

        # Pasar evento a Bolt
        return handler.handle(request)

    except Exception as e:
        print("💥 Error in /slack/events:", e)
        return make_response("Internal Server Error", 500)


# === HANDLER DE MENSAJES ===
@bolt_app.event("message")
def handle_message(event, say):
    if event.get("subtype") is None:
        text = event.get("text")
        prompt = f"Eres un experto en resolver problemas de Meta. Un usuario escribió: '{text}'. Respondé brevemente con una posible ayuda o sugerencia. Si no hay suficiente información, responde con 'No puedo ayudarte con eso'."

        try:
            completion = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            response = completion.choices[0].message.content
            say(thread_ts=event["ts"], text=response + "\n¿Te sirvió esta info?")
        except Exception as e:
            say(thread_ts=event["ts"], text=f"⚠️ Error procesando el mensaje: {e}")


# === MAIN ===
if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
