from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from googletrans import Translator

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Permite conexões de qualquer origem (necessário para ngrok)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

translator = Translator()
connections = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)

    nome = "Usuário"
    idioma = "en"

    try:
        # Recebe os dados iniciais do cliente (nome e idioma)
        data = await websocket.receive_json()
        nome = data.get("nome", "Usuário")
        idioma = data.get("idioma", "en")
        print(f"🌍 {nome} conectado, idioma: {idioma}")

        while True:
            msg = await websocket.receive_json()
            texto = msg.get("texto")
            src_lang = msg.get("idioma", "en")

            print(f"📩 {nome}: {texto}")

            # Traduz e envia para todos os outros conectados
            for conn in connections:
                if conn != websocket:
                    dest_lang = "pt" if src_lang != "pt" else "en"
                    traducao = translator.translate(texto, src=src_lang, dest=dest_lang).text
                    await conn.send_json({
                        "de": nome,
                        "texto": traducao,
                        "idioma": dest_lang
                    })

    except WebSocketDisconnect:
        print(f"❌ {nome} desconectado.")
        connections.remove(websocket)
