@echo off
cd /d "%~dp0"
call "%~dp0localizar_python.bat"
if errorlevel 1 (
  pause
  exit /b 1
)
"%JARVIS_PYTHON%" diagnostico.py
pause
