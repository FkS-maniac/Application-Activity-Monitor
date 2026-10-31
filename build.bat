@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe -m pip install pyinstaller
.venv\Scripts\python.exe -m PyInstaller --clean --onefile --noconsole --collect-all ttkbootstrap --hidden-import=win32com.client --hidden-import=pythoncom --name GameSessionTracker main.py
pause
