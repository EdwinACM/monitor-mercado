#!/bin/bash
# Doble clic para abrir el Monitor de Mercado.
cd "$(dirname "$0")"
VENV="$HOME/.monitor_mercado/venv"
if [ ! -x "$VENV/bin/python" ]; then
  echo "Primera vez: preparando el entorno de Python…"
  python3 -m venv "$VENV" && "$VENV/bin/pip" install -q -r requirements.txt || { echo "No se pudo instalar."; read -r; exit 1; }
fi
(sleep 1.5; open "http://localhost:8765") &
exec "$VENV/bin/python" server.py
