from playwright.sync_api import sync_playwright
import time
import json

mensajes_capturados = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    # Interceptamos todos los mensajes WebSocket
    def on_websocket(ws):
        print(f"WebSocket conectado: {ws.url}")
        
        def on_message(payload):
            # Solo guardamos mensajes que parezcan tener cuotas
            if len(payload) > 100:
                mensajes_capturados.append(payload)
                print(f"Mensaje recibido ({len(payload)} chars): {payload[:200]}")
        
        ws.on("framereceived", on_message)

    page.on("websocket", on_websocket)

    print("Abriendo Winamax...")
    page.goto("https://www.winamax.es/apuestas-deportivas/sports/1/7/4")
    
    print("Esperando mensajes WebSocket durante 15 segundos...")
    time.sleep(15)

    # Guardamos todos los mensajes en un archivo
    with open("winamax_websocket.txt", "w", encoding="utf-8") as f:
        for i, msg in enumerate(mensajes_capturados):
            f.write(f"--- MENSAJE {i+1} ---\n")
            f.write(msg + "\n\n")

    print(f"Total mensajes capturados: {len(mensajes_capturados)}")
    print("Guardados en winamax_websocket.txt")
    
    browser.close()