from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from deep_translator import GoogleTranslator
from gtts import gTTS
import os, json, uuid

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

connections = []  # [{ "id":..., "ws":..., "lang":... }]

@app.get("/")
async def home():
    return HTMLResponse(open("static/index.html", "r", encoding="utf-8").read())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_id = str(uuid.uuid4())[:8]
    conn_info = {"id": client_id, "ws": websocket, "lang": None}
    connections.append(conn_info)
    print(f"🔗 Novo cliente conectado: {client_id}")

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            # Registro de idioma
            if msg.get("type") == "register":
                conn_info["lang"] = msg["lang"]
                await websocket.send_text(json.dumps({"type": "system", "msg": f"Idioma registrado: {msg['lang']}"}))
                print(f"🆔 Cliente {client_id} registrou idioma {msg['lang']}")
                continue

            # Mensagem normal
            if msg.get("type") == "message":
                text = msg.get("text", "")
                sender_lang = conn_info["lang"] or "auto"
                print(f"📨 Mensagem recebida ({sender_lang}): {text}")

                for other in connections:
                    if other["ws"] == websocket:
                        continue  # não enviar pra si mesmo

                    target_lang = other.get("lang", "en")
                    try:
                        translated = GoogleTranslator(source=sender_lang, target=target_lang).translate(text)
                    except Exception as e:
                        print("⚠️ Erro na tradução:", e)
                        translated = text

                    # Gera áudio na língua do receptor
                    audio_file = f"static/audio_{uuid.uuid4().hex[:8]}.mp3"
                    try:
                        tts = gTTS(translated, lang=target_lang)
                        tts.save(audio_file)
                    except Exception as e:
                        print("⚠️ Erro gTTS:", e)
                        audio_file = None

                    payload = {
                        "type": "translation",
                        "from_id": client_id,
                        "from_lang": sender_lang,
                        "original": text,
                        "translated": translated,
                        "target_lang": target_lang,
                        "audio": f"/{audio_file}" if audio_file else None
                    }
                    await other["ws"].send_text(json.dumps(payload))
                    print(f"➡️ Enviado para {other['id']} ({target_lang})")

    except Exception as e:
        print(f"⚠️ Erro: {e}")
    finally:
        connections.remove(conn_info)
        print(f"❌ Cliente desconectado: {client_id}")
