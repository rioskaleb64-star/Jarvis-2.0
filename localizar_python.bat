@echo off
set "JARVIS_PYTHON="
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" set "JARVIS_PYTHON=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
if defined JARVIS_PYTHON exit /b 0
for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "JARVIS_PYTHON=%%P"
if defined JARVIS_PYTHON exit /b 0
for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "JARVIS_PYTHON=%%P"
if defined JARVIS_PYTHON exit /b 0
echo Python nao encontrado. Instale Python em python.org e habilite Add Python to PATH.
exit /b 1
