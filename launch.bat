@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m mistral_desktop
) else (
    python -m mistral_desktop
)
pause
