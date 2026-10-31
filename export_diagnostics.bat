@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe -m src.utils.diagnostics --output diagnostics.txt
pause
