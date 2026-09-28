@echo off
cd /d "%~dp0"
call "%~dp0localizar_python.bat"
if errorlevel 1 (
  pause
  exit /b 1
)
set "JARVIS_PYTHONW=%JARVIS_PYTHON:python.exe=pythonw.exe%"
if exist "%JARVIS_PYTHONW%" (
  start "" "%JARVIS_PYTHONW%" "%~dp0jarvis_listener.py"
) else (
  start "" "%JARVIS_PYTHON%" "%~dp0jarvis_listener.py"
)
