# Función de Vercel para /api/estado: reutiliza el manejador de server.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from server import Handler as handler  # noqa: E402,F401
