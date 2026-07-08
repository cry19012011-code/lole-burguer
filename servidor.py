#!/usr/bin/env python3
"""
Lole Burger — Servidor WebSocket
Conecta el menú del cliente con la pantalla de cocina.

USO:
  1. Instalá Python 3 si no lo tenés: https://python.org
  2. Instalá la dependencia:  pip install websockets
  3. Corré este archivo:      python servidor.py
  4. Abrí menu.html en el cel (o cualquier dispositivo de la red)
  5. Abrí cocina.html en la TV / Smart TV
  La IP de tu PC aparece en consola al iniciar.
"""

import asyncio
import json
import websockets
import socket
import datetime

# ─── Configuración ───────────────────────────────────────────────
HOST = "0.0.0.0"   # Escucha en todas las interfaces de red
PORT = 8765
# ─────────────────────────────────────────────────────────────────

clientes = set()
cocinas  = set()
contador_pedido = 0

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

async def handler(ws):
    global contador_pedido
    tipo = None

    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            accion = msg.get("accion")

            # ── Registro de conexión ──────────────────────────────
            if accion == "registrar":
                tipo = msg.get("tipo")  # "menu" | "cocina"
                if tipo == "cocina":
                    cocinas.add(ws)
                    print(f"[{now()}] 🍳  Cocina conectada   ({len(cocinas)} activa/s)")
                    await ws.send(json.dumps({"accion": "bienvenida", "msg": "Cocina conectada"}))
                else:
                    clientes.add(ws)
                    print(f"[{now()}] 📱  Cliente conectado  ({len(clientes)} activo/s)")

            # ── Nuevo pedido ──────────────────────────────────────
            elif accion == "pedido":
                contador_pedido += 1
                numero = contador_pedido

                pedido = {
                    "accion":  "nuevo_pedido",
                    "numero":  numero,
                    "hora":    now(),
                    "mesa":    msg.get("mesa", ""),
                    "nota":    msg.get("nota", ""),
                    "items":   msg.get("items", []),
                    "total":   msg.get("total", 0),
                }

                print(f"[{now()}] 🔔  Pedido #{numero:03d} recibido — Gs. {pedido['total']:,}")
                for it in pedido["items"]:
                    print(f"          • {it['qty']}x {it['nombre']}")

                # Confirmar al cliente
                await ws.send(json.dumps({
                    "accion": "confirmado",
                    "numero": numero,
                }))

                # Enviar a TODAS las pantallas de cocina
                if cocinas:
                    muertos = set()
                    for cocina in cocinas:
                        try:
                            await cocina.send(json.dumps(pedido))
                        except Exception:
                            muertos.add(cocina)
                    cocinas.difference_update(muertos)
                else:
                    print(f"[{now()}] ⚠️   Sin cocina conectada — pedido #{numero:03d} en cola")

            # ── Pedido listo (cocina marca como terminado) ────────
            elif accion == "listo":
                numero = msg.get("numero")
                print(f"[{now()}] ✅  Pedido #{numero:03d} marcado como LISTO")
                # Notificar a todos los clientes (para futuras mejoras)
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
    ip = get_local_ip()
    print("=" * 55)
    print("  🍔  Lole Burger — Servidor de pedidos")
    print("=" * 55)
    print(f"  IP local:  {ip}")
    print(f"  Puerto:    {PORT}")
    print()
    print("  Abrí estas URLs en tu red WiFi:")
    print(f"  📱  Menú (cel/caja):  abrir menu.html")
    print(f"      (el archivo lee la IP automáticamente)")
    print(f"  📺  Cocina (TV):      abrir cocina.html")
    print()
    print("  Esperando conexiones... (Ctrl+C para salir)")
    print("=" * 55)

    async with websockets.serve(handler, HOST, PORT):
        await asyncio.Future()  # corre para siempre

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n  Servidor detenido.")