@echo off
setlocal

cd /d "%~dp0"

echo [BACnet Simulator] Preparing Python environment...

if not exist ".venv\Scripts\python.exe" (
  echo [BACnet Simulator] Creating .venv with Python 3.11...
  py -3.11 -m venv .venv
  if errorlevel 1 (
    echo [BACnet Simulator] Failed to create venv with Python 3.11.
    echo [BACnet Simulator] Make sure Python 3.11 is installed.
    pause
    exit /b 1
  )
)

echo [BACnet Simulator] Installing/updating requirements...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [BACnet Simulator] Dependency install failed.
  pause
  exit /b 1
)

echo [BACnet Simulator] Launching app...
".venv\Scripts\python.exe" main.py

endlocal
