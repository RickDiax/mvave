@echo off
setlocal
title MK300 Studio
cd /d "%~dp0"
if exist "windows\.venv-midi\Scripts\python.exe" goto open_studio
echo Preparando as dependencias do MK300 Studio pela primeira vez...
call "%~dp0windows\instalar.cmd"
if errorlevel 1 exit /b 1
:open_studio
call "%~dp0windows\abrir-studio.cmd"
