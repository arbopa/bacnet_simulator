@echo off
setlocal

cd /d "%~dp0"

set "BUILD_VENV=.venv-build311"
set "PY_EXE=%BUILD_VENV%\Scripts\python.exe"

echo [BACsim] Preparing build environment...

if not exist "%PY_EXE%" (
  echo [BACsim] Creating build venv using Python 3.11...
  py -3.11 -m venv "%BUILD_VENV%"
  if errorlevel 1 (
    echo [BACsim] Python 3.11 venv creation failed.
    echo [BACsim] Install Python 3.11 and ensure py launcher can run: py -3.11
    pause
    exit /b 1
  )
)

echo [BACsim] Verifying build interpreter version...
"%PY_EXE%" -c "import sys; raise SystemExit(0 if sys.version_info[:2]==(3,11) else 1)"
if errorlevel 1 (
  echo [BACsim] Build venv is not Python 3.11.
  echo [BACsim] Delete %BUILD_VENV% and rerun after installing Python 3.11.
  pause
  exit /b 1
)

echo [BACsim] Installing build dependencies...
"%PY_EXE%" -m pip --version >nul 2>&1
if errorlevel 1 (
  echo [BACsim] pip missing in build venv, trying ensurepip...
  "%PY_EXE%" -m ensurepip --upgrade
)

"%PY_EXE%" -m pip install --upgrade pip
"%PY_EXE%" -m pip install -r requirements.txt
"%PY_EXE%" -m pip install pyinstaller
if errorlevel 1 (
  echo [BACsim] Dependency install failed.
  pause
  exit /b 1
)

echo [BACsim] Verifying bacpypes3 in build venv...
"%PY_EXE%" -m pip show bacpypes3 >nul 2>&1
if errorlevel 1 (
  echo [BACsim] bacpypes3 is missing in build venv. Build cannot continue.
  pause
  exit /b 1
)

echo [BACsim] Building executable...
"%PY_EXE%" -m PyInstaller --noconfirm --clean bacsim.spec
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
