from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request
import openai
import requests
import json
import os

# Config desde variables de entorno (más seguro)
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
openai.api_key = OPENAI_API_KEY
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

@app.event("message")
def handle_message(event, say):
    if event.get("subtype") is None and "meta-blockers" in event.get("channel", ""):
        user_message = event["text"]

        prompt = f"""
        Sos un compañero experto en resolver bloqueos internos.
        Alguien escribió: "{user_message}".
        Respondé con claridad y pasos concretos. 
        Al final, preguntá: "¿Te sirvió esta info?".
        """

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        reply = response.choices[0].message.content
        say(thread_ts=event["ts"], text=reply)

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
        requests.post(notion_url, headers=headers, data=json.dumps(data))

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=3000)
