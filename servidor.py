#!/usr/bin/env python3
"""
Lole Burger — Servidor combinado HTTP + WebSocket
Sirve los archivos HTML y maneja pedidos en tiempo real.
"""

import asyncio
import json
import os
import datetime
import websockets
from http.server import SimpleHTTPRequestHandler
import socketserver
import threading

PORT = int(os.environ.get("PORT", 8765))

clientes = set()
cocinas  = set()
contador_pedido = 0

# ── Servidor HTTP para los archivos HTML ──────────────────────────
class Handler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # silenciar logs HTTP

def iniciar_http():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()

# ── WebSocket ─────────────────────────────────────────────────────
WS_PORT = PORT + 1 if PORT != 443 else 8766

async def handler(ws):
    global contador_pedido
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            accion = msg.get("accion")

            if accion == "registrar":
                tipo = msg.get("tipo")
                if tipo == "cocina":
                    cocinas.add(ws)
                    print(f"[{now()}] Cocina conectada ({len(cocinas)} activa/s)")
                    await ws.send(json.dumps({"accion": "bienvenida"}))
                else:
                    clientes.add(ws)
                    print(f"[{now()}] Cliente conectado ({len(clientes)} activo/s)")

            elif accion == "pedido":
                contador_pedido += 1
                numero = contador_pedido
                pedido = {
                    "accion": "nuevo_pedido",
                    "numero": numero,
                    "hora":   now(),
                    "mesa":   msg.get("mesa", ""),
                    "nota":   msg.get("nota", ""),
                    "items":  msg.get("items", []),
                    "total":  msg.get("total", 0),
                }
                print(f"[{now()}] Pedido #{numero:03d} — Gs. {pedido['total']:,}")
                await ws.send(json.dumps({"accion": "confirmado", "numero": numero}))
                muertos = set()
                for cocina in cocinas:
                    try:
                        await cocina.send(json.dumps(pedido))
                    except Exception:
                        muertos.add(cocina)
                cocinas.difference_update(muertos)

            elif accion == "listo":
                numero = msg.get("numero")
                print(f"[{now()}] Pedido #{numero:03d} LISTO")
                muertos = set()
                for c in clientes:
                    try:
                        await c.send(json.dumps({"accion": "listo", "numero": numero}))
                    except Exception:
                        muertos.add(c)
                clientes.difference_update(muertos)

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        clientes.discard(ws)
        cocinas.discard(ws)

def now():
    return datetime.datetime.now().strftime("%H:%M:%S")

async def main():
    print(f"Lole Burger arriba — HTTP:{PORT}  WS:{WS_PORT}")
    # HTTP en hilo separado
    t = threading.Thread(target=iniciar_http, daemon=True)
    t.start()
    # WebSocket
    async with websockets.serve(handler, "0.0.0.0", WS_PORT):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())