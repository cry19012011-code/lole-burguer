#!/usr/bin/env python3
"""
Lole Burger — Servidor unificado HTTP + WebSocket en un solo puerto
"""
import asyncio
import json
import os
import datetime
import websockets
from websockets.server import serve
from http.server import SimpleHTTPRequestHandler
import io

PORT = int(os.environ.get("PORT", 8765))

clientes = set()
cocinas  = set()
contador_pedido = 0

def now():
    return datetime.datetime.now().strftime("%H:%M:%S")

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
                    print(f"[{now()}] Cocina conectada ({len(cocinas)})")
                    await ws.send(json.dumps({"accion": "bienvenida"}))
                else:
                    clientes.add(ws)
                    print(f"[{now()}] Cliente conectado ({len(clientes)})")

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
                print(f"[{now()}] Pedido #{numero:03d}")
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

async def http_handler(path, request_headers):
    """Sirve archivos estáticos para peticiones HTTP normales"""
    # Solo responder a peticiones que no son WebSocket upgrade
    return None  # dejar que websockets maneje el WS

async def process_request(connection, request):
    """Intercepta requests HTTP y sirve archivos"""
    path = request.path.lstrip("/") or "menu.html"
    # Quitar query strings
    path = path.split("?")[0]

    # Mapeo de extensiones a content-type
    tipos = {
        "html": "text/html; charset=utf-8",
        "css":  "text/css",
        "js":   "application/javascript",
        "png":  "image/png",
        "jpg":  "image/jpeg",
        "ico":  "image/x-icon",
    }
    ext = path.rsplit(".", 1)[-1] if "." in path else "html"
    content_type = tipos.get(ext, "text/plain")

    base = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(base, path)

    if os.path.isfile(filepath):
        with open(filepath, "rb") as f:
            body = f.read()
        from websockets.http11 import Response
        headers = [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
            ("Access-Control-Allow-Origin", "*"),
        ]
        return Response(200, "OK", headers, body)

    # 404
    from websockets.http11 import Response
    body = b"Not found"
    return Response(404, "Not Found", [("Content-Type","text/plain"),("Content-Length","9")], body)

async def main():
    print(f"Lole Burger corriendo en puerto {PORT}")
    async with serve(handler, "0.0.0.0", PORT, process_request=process_request):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())