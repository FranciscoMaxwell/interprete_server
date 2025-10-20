from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from deep_translator import GoogleTranslator
from gtts import gTTS
import os, json, asyncio, uuid

app = FastAPI()

# Pasta de arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Conexões: lista de dicts { "ws": WebSocket, "lang": "pt", "id": "..."}
connections = []

@app.get("/")
async def home():
    return HTMLResponse(open("static/index.html", "r", encoding="utf-8").read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_id = str(uuid.uuid4())[:8]
    conn_info = {"ws": websocket, "lang": None, "id": client_id}
    connections.append(conn_info)
    print(f"🔗 Conexão iniciada: {client_id}")

    try:
        # Primeiro, aguardar o cliente enviar registro de idioma
        register_msg = await websocket.receive_text()
        try:
            reg = json.loads(register_msg)
        except:
            reg = None

        if reg and reg.get("type") == "register" and reg.get("lang"):
            conn_info["lang"] = reg["lang"]
            await websocket.send_text(json.dumps({"type":"system","msg":"registered","id": client_id}))
            print(f"🆔 Cliente {client_id} registrou idioma: {conn_info['lang']}")
        else:
            # Se não registrou, definimos inglês por padrão (pode ajustar)
            conn_info["lang"] = "en"
            await websocket.send_text(json.dumps({"type":"system","msg":"registered_default_en","id": client_id}))
            print(f"🆔 Cliente {client_id} usou idioma padrão: en")

        # Loop principal: receber mensagens do cliente
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            # Esperamos mensagens do tipo { type: "message", text: "..." }
            if data.get("type") != "message":
                continue

            text = data.get("text", "").strip()
            if not text:
                continue

            sender_lang = conn_info["lang"] or "auto"
            print(f"📨 Mensagem de {conn_info['id']} (lang={sender_lang}): {text}")

            # Para cada outra conexão, traduzir para o idioma que ela declarou
            for other in connections:
                other_ws = other["ws"]
                # pular o remetente
                if other_ws == websocket:
                    continue

                target_lang = other.get("lang") or "en"
                try:
                    # Traduzir (source auto)
                    translated = GoogleTranslator(source="auto", target=target_lang).translate(text)
                except Exception as e:
                    print("⚠️ Erro na tradução:", e)
                    translated = text  # fallback: enviar original

                # Gerar áudio em um arquivo único (por idioma + uuid)
                audio_filename = f"audio_{uuid.uuid4().hex[:10]}_{target_lang}.mp3"
                audio_path = os.path.join("static", audio_filename)
                try:
                    tts = gTTS(translated, lang=target_lang)
                    tts.save(audio_path)
                except Exception as e:
                    print("⚠️ Erro gTTS:", e)
                    audio_path = None

                payload = {
                    "type": "translation",
                    "from_id": conn_info["id"],
                    "from_lang": sender_lang,
                    "original": text,
                    "translated": translated,
                    "audio": f"/static/{audio_filename}" if audio_path else None,
                    "target_lang": target_lang
                }

                # Enviar para o outro cliente
                try:
                    await other_ws.send_text(json.dumps(payload))
                    print(f"➡️ Enviado para {other['id']} (lang={target_lang})")
                except Exception as e:
                    print("⚠️ Erro enviando para cliente:", e)

    except Exception as e:
        print("⚠️ Erro websocket geral:", e)

    finally:
        # remover conexão e fechar se ainda aberta
        try:
            connections.remove(conn_info)
        except:
            pass
        try:
            await websocket.close()
        except:
            pass
        print(f"❌ Cliente desconectado: {client_id}")
