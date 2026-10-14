@echo off
setlocal
title MK300 Studio
cd /d "%~dp0"
if not exist ".venv-midi\Scripts\python.exe" (
  echo Execute instalar.cmd primeiro. Depois abra este arquivo novamente.
  pause
  exit /b 1
)
".venv-midi\Scripts\python.exe" "..\studio\server.py"
if errorlevel 1 pause
