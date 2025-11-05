from flask import Flask, request, make_response
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from openai import OpenAI
import os
import requests

# === CONFIG ===
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

client_ai = OpenAI(api_key=OPENAI_API_KEY)

# === INIT ===
bolt_app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)


# === HEALTHCHECK ===
@flask_app.route("/", methods=["GET"])
def home():
    return "✅ Meta Solver online"


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.get_json()
    print("📩 Incoming Slack event:", data)
    if data and "challenge" in data:
        return make_response(data["challenge"], 200, {"content_type": "text/plain"})
    return handler.handle(request)


# === FUNCIONES AUXILIARES ===
def guardar_feedback_en_notion(user, message):
    """Guarda mensajes tipo 'gracias' o 'me sirvió' en Notion."""
    try:
        notion_url = "https://api.notion.com/v1/pages"
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        data = {
            "parent": {"database_id": NOTION_DATABASE_ID},
            "properties": {
                "Usuario": {"title": [{"text": {"content": user}}]},
                "Mensaje": {"rich_text": [{"text": {"content": message}}]},
                "Tipo": {"select": {"name": "Agradecimiento"}}
            }
        }
        requests.post(notion_url, headers=headers, json=data)
        print(f"📝 Feedback guardado en Notion: {user} - {message}")
    except Exception as e:
        print("⚠️ Error guardando feedback en Notion:", e)


# === EVENTOS SLACK ===
@bolt_app.event("message")
def handle_message_events(body, say, client, event):
    try:
        if event.get("subtype") == "bot_message":
            return

        text = event.get("text", "").lower()
        if not text:
            return

        user = event.get("user")
        channel = event.get("channel")
        parent_ts = event["thread_ts"] if event.get("thread_ts") else event["ts"]

        # 👀 Reaccionar al mensaje original
        try:
            client.reactions_add(channel=channel, timestamp=event["ts"], name="eyes")
        except Exception as e:
            print("⚠️ No se pudo agregar reacción:", e)

        # 🙌 Si es mensaje de agradecimiento
        if any(palabra in text for palabra in ["gracias", "me sirvió", "genial", "perfecto", "buenísimo"]):
            client.reactions_add(channel=channel, timestamp=event["ts"], name="raised_hands")
            say(thread_ts=parent_ts, text="🙌 ¡Me alegra que haya servido!")
            guardar_feedback_en_notion(user, text)
            return

        # 🧠 Prompt optimizado + búsqueda web real
        prompt = f"""
Sos Meta Solver, un asistente técnico del equipo de Darwin AI que ayuda a resolver problemas con Meta,
Meta Business Manager y la API de WhatsApp Business (conexión, permisos, tokens, co-existence, etc.).

Respondé **de forma corta y accionable**, en español.
🔹 Si el problema es claro, da solo los pasos concretos para resolverlo.  
🔹 Si falta info, pedí puntualmente lo que necesites.  
🔹 Solo compartí links **oficiales y verificados**. Si no hay, decí: “no encontré un link oficial disponible”.

Mensaje del usuario:
\"\"\"{text}\"\"\"
"""

        completion = client_ai.chat.completions.create(
            model="gpt-5",  # Usa GPT-5 con búsqueda web real
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sos Meta Solver, un asistente técnico del equipo de Darwin AI. "
                        "Usá la búsqueda web integrada para compartir únicamente links reales "
                        "de Meta o Facebook for Developers."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            tools=[{"type": "web-search"}],
            max_tokens=200,
        )

        response_text = completion.choices[0].message.content.strip()
        say(text=response_text, thread_ts=parent_ts)

    except Exception as e:
        print("💥 Error en handle_message_events:", e)
        say(thread_ts=event.get("ts"), text=f"⚠️ Error procesando el mensaje: {e}")


# === MAIN ===
if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
