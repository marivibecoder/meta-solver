from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, make_response
import openai
import requests
import json
import os

# === CONFIGURACIÓN ===
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# === INICIALIZACIÓN ===
bolt_app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
openai.api_key = OPENAI_API_KEY
flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)


# === EVENTO: NUEVOS MENSAJES EN SLACK ===
@app.event("message")
def handle_message(event, say):
    if event.get("subtype") is None:  # evita mensajes del sistema
        user_message = event["text"]

        prompt = f"""
        Sos un especialista en resolver problemas relacionados a Meta (Business Manager, Lineas de WhatsApp por la API, coexistance, etc).
        Alguien escribió: "{user_message}".
        Respondé con claridad, pasos concretos y amabilidad.
        Al final, preguntá: "Te sirvió esta info?".
        """

        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            reply = response.choices[0].message.content
            say(thread_ts=event["ts"], text=reply)
        except Exception as e:
            say(thread_ts=event["ts"], text=f"Hubo un error procesando el mensaje: {e}")

# === EVENTO: REACCIÓN CON ✅ PARA GUARDAR EN NOTION ===
@app.event("reaction_added")
def handle_reaction(event, say):
    if event["reaction"] == "white_check_mark":
        message_text = "Respuesta validada como útil"
        notion_url = "https://api.notion.com/v1/pages"
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        data = {
            "parent": {"database_id": NOTION_DATABASE_ID},
            "properties": {
                "Title": {"title": [{"text": {"content": message_text}}]},
                "Source": {"rich_text": [{"text": {"content": "Slack"}}]},
            }
        }
        try:
            requests.post(notion_url, headers=headers, data=json.dumps(data))
        except Exception as e:
            print(f"Error guardando en Notion: {e}")

# === ENDPOINT PARA EVENTOS DE SLACK ===
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.get_json()
    if data and "challenge" in data:
        return make_response(data["challenge"], 200, {"content_type": "text/plain"})
    return handler.handle(request)




