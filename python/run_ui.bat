@echo off
set SCRIPT_DIR=%~dp0
set WORKSPACE=%SCRIPT_DIR%workspace
set PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if not exist "%PY%" set PY=python
set PYTHONPATH=%SCRIPT_DIR%
if not exist "%WORKSPACE%" mkdir "%WORKSPACE%"
cd /d "%SCRIPT_DIR%"
"%PY%" -m pip install -r "%SCRIPT_DIR%requirements.txt" -q
echo Starting DMI2Map UI at http://127.0.0.1:8765
echo Workspace: %WORKSPACE%
"%PY%" -m dmi2map ui --root "%WORKSPACE%"
pause
