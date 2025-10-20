from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from deep_translator import GoogleTranslator
from gtts import gTTS
import os, json, asyncio

app = FastAPI()

# Pasta de arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Lista global de conexões
connections = []

@app.get("/")
async def home():
    return HTMLResponse(open("static/index.html", "r", encoding="utf-8").read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)
    print("🔗 Novo cliente conectado.")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            text = message["text"]
            lang = message["lang"]

            print(f"🗣️ Mensagem recebida: {text} → {lang}")

            # Traduz automaticamente
            translated = GoogleTranslator(source="auto", target=lang).translate(text)

            # Cria áudio com gTTS
            audio_file = f"static/audio_{id(websocket)}.mp3"
            tts = gTTS(translated, lang=lang)
            tts.save(audio_file)

            # Envia para todos os outros clientes conectados
            for conn in connections:
                if conn != websocket:
                    await conn.send_json({
                        "translated": translated,
                        "audio": f"/{audio_file}"
                    })

    except Exception as e:
        print(f"⚠️ Erro: {e}")
    finally:
        connections.remove(websocket)
        await websocket.close()
        print("❌ Cliente desconectado")
