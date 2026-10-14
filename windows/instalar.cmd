@echo off
setlocal
cd /d "%~dp0"
echo Preparacao MK-300 Windows - Python 3.11 ou superior
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 goto python_missing
if exist ".venv\Scripts\python.exe" goto dependencies
py -3 -m venv .venv
if errorlevel 1 goto failed
:dependencies
".venv\Scripts\python.exe" -m pip install "mido>=1.3,<2" "python-rtmidi>=1.5,<2"
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -c "import mido, rtmidi; print('Dependencias MIDI prontas.')"
if errorlevel 1 goto failed
echo Instalacao concluida. Conecte a MK-300 por USB, feche M-EFCS e abra testar.cmd.
pause
exit /b 0
:python_missing
echo Instale Python 3.11 ou superior de https://www.python.org/downloads/windows/
echo Inclua o Python Launcher na instalacao. Depois execute este arquivo novamente.
pause
exit /b 1
:failed
echo Falha na preparacao. Copie a mensagem acima para analisarmos.
pause
exit /b 1
