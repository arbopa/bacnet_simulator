@echo off
setlocal

cd /d "%~dp0"

echo [BACsim] Preparing build environment...

if not exist ".venv-build\Scripts\python.exe" (
  echo [BACsim] Creating build venv using py launcher...
  py -3 -m venv .venv-build
  if errorlevel 1 (
    echo [BACsim] py launcher venv creation failed, trying python -m venv...
    python -m venv .venv-build
    if errorlevel 1 (
      echo [BACsim] Failed to create build venv.
      pause
      exit /b 1
    )
  )
)

echo [BACsim] Installing build dependencies...
".venv-build\Scripts\python.exe" -m pip --version >nul 2>&1
if errorlevel 1 (
  echo [BACsim] pip missing in build venv, trying ensurepip...
  ".venv-build\Scripts\python.exe" -m ensurepip --upgrade
)

".venv-build\Scripts\python.exe" -m pip install --upgrade pip
".venv-build\Scripts\python.exe" -m pip install -r requirements.txt
".venv-build\Scripts\python.exe" -m pip install pyinstaller
if errorlevel 1 (
  echo [BACsim] Dependency install failed.
  pause
  exit /b 1
)
echo [BACsim] Verifying bacpypes3 in build venv...
".venv-build\Scripts\python.exe" -m pip show bacpypes3 >nul 2>&1
if errorlevel 1 (
  echo [BACsim] bacpypes3 is missing in build venv. Build cannot continue.
  pause
  exit /b 1
)
echo [BACsim] Building executable...
".venv-build\Scripts\python.exe" -m PyInstaller --noconfirm --clean bacsim.spec
if errorlevel 1 (
  echo [BACsim] Build failed.
  pause
  exit /b 1
)

echo.
echo [BACsim] Build complete.
echo [BACsim] Executable: dist\BACsim\BACsim.exe
echo [BACsim] Folder to distribute: dist\BACsim\

endlocal
