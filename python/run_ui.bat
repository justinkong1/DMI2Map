@echo off
set ROOT=%~dp0..
set PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if not exist "%PY%" set PY=python
set PYTHONPATH=%~dp0
cd /d "%ROOT%"
"%PY%" -m pip install -r "%~dp0requirements.txt" -q
echo Starting DMI2Map UI at http://127.0.0.1:8765
"%PY%" -m dmi2map ui --root "%ROOT%"
pause
