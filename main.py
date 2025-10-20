from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from deep_translator import GoogleTranslator
from gtts import gTTS
import os

app = FastAPI()

# Montar pasta de arquivos estáticos (HTML, etc)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def home():
    return HTMLResponse(open("static/index.html", "r", encoding="utf-8").read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🔗 Cliente conectado via WebSocket")

    try:
        while True:
            data = await websocket.receive_text()

            # Detectar idioma e traduzir
            translated = GoogleTranslator(source='auto', target='en').translate(data)

            # Criar voz com gTTS
            tts = gTTS(translated)
            audio_path = "audio.mp3"
            tts.save(audio_path)

            # Responder com texto traduzido
            await websocket.send_text(translated)
            print(f"Mensagem recebida: {data} → {translated}")

    except Exception as e:
        print(f"⚠️ Erro: {e}")
    finally:
        await websocket.close()
        print("🔌 Cliente desconectado")
