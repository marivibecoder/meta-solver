from flask import Flask, request, make_response
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from openai import OpenAI
import os
import json

# === CONFIGURACIÓN ===
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
client_ai = OpenAI(api_key=OPENAI_API_KEY)

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
        prompt = f"""
Sos Meta Solver, un asistente técnico del equipo de Darwin AI que ayuda a los miembros del equipo a resolver problemas relacionados con Meta, WhatsApp Business API y sus integraciones.

Tu trabajo es leer los mensajes que se publican en el canal #meta-blockers y responder de forma **clara, útil y empática** en español.

Usá **toda la información general y técnica que conozcas** para resolver el problema, incluso si no está explícita en el mensaje.  
Siempre que sea posible, **incluí links oficiales o recursos confiables** (por ejemplo, documentación de Meta, Facebook for Developers, o guías de soporte reconocidas).

**Tu tono:** profesional pero cercano, con lenguaje natural y directo.  
**Formato de respuesta:**
1. Identificá en 1 línea cuál es el problema o error.
2. Explicá posibles causas o motivos comunes.
3. Proponé pasos concretos o soluciones prácticas.
4. Si no podés resolverlo con certeza, indicá a qué persona o equipo derivar (por ejemplo, “@soporte-meta”).

Ejemplo de estilo:
"👋 Hola! Parece un problema con la conexión del número a la API de WhatsApp.  
Esto suele pasar cuando la cuenta de Business Manager no tiene permisos de administrador o el token expiró.  
Podés revisar los accesos acá: https://developers.facebook.com/docs/whatsapp/cloud-api/guides/business-accounts  
Si sigue igual, pingueá a @soporte-meta para revisar los permisos."

Mensaje recibido:
{user_message}
"""
       completion = client_ai.chat.completions.create(
    model="gpt-4o",
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
