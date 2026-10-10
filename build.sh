#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo 'Crea .venv e instala requirements-dev.txt primero.' >&2
  exit 1
fi
.venv/bin/python -m PyInstaller --clean --noconfirm --onefile --windowed --name SpotyVManager --collect-all customtkinter --copy-metadata anthropic run_app.py
echo 'Ejecutable en dist/. Configura .env junto al ejecutable; no se incluye en el archivo.'
