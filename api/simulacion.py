# Función de Vercel: ruta /api/simulacion
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server  # noqa: E402


class handler(BaseHTTPRequestHandler):
    do_GET = server.Handler.do_GET
    send = server.Handler.send

    def log_message(self, *args):
        pass
