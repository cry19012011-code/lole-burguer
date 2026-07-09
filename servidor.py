#!/usr/bin/env python3
import http.server
import os

PORT = int(os.environ.get("PORT", 8080))

os.chdir(os.path.dirname(os.path.abspath(__file__)))

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

print(f"Servidor corriendo en puerto {PORT}")
http.server.HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()