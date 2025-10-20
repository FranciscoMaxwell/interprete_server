from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from googletrans import Translator
from gtts import gTTS
import tempfile
import os

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

translator = Translator()
connections = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)

    try:
        data = await websocket.receive_json()
        idioma = data.get("idioma", "en")
        nome = data.get("nome", "Usuário")
        print(f"🌍 {nome} conectado, idioma: {idioma}")

        while True:
            msg = await websocket.receive_json()
            texto = msg["texto"]
            src_lang = msg["idioma"]

            print(f"📩 {nome}: {texto}")

            # Traduz para todos os outros conectados
            for conn in connections:
                if conn != websocket:
                    dest_lang = "pt" if src_lang != "pt" else "en"
                    traducao = translator.translate(texto, src=src_lang, dest=dest_lang).text

                    # Gera áudio
                    tts = gTTS(traducao, lang=dest_lang)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                        tts.save(f.name)
                        audio_path = f.name

                    await conn.send_json({
                        "de": nome,
                        "texto": traducao,
                        "idioma": dest_lang,
                        "audio": f"/static/{os.path.basename(audio_path)}"
                    })

    except WebSocketDisconnect:
        print(f"❌ {nome} desconectado.")
        connections.remove(websocket)
