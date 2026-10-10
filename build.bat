@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Crea .venv e instala requirements-dev.txt primero.
  exit /b 1
)
".venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm --onefile --windowed --name SpotyVManager --collect-all customtkinter --copy-metadata openai run_app.py
if errorlevel 1 exit /b 1
echo Ejecutable: dist\SpotyVManager.exe
echo Configura .env junto al ejecutable; no esta incluido en el archivo.
