@echo off
setlocal
cd /d "%~dp0"
echo Preparacao MK-300 Windows - Python 3.12 ou 3.11 x64
set "mk300_python_tag="
py -3.12 -c "import sys,platform; sys.exit(0 if sys.implementation.name == 'cpython' and sys.maxsize > 2**32 and platform.machine().lower() in ('amd64','x86_64') else 1)" >nul 2>&1
if not errorlevel 1 set "mk300_python_tag=-3.12"
if defined mk300_python_tag goto interpreter_ready
py -3.11 -c "import sys,platform; sys.exit(0 if sys.implementation.name == 'cpython' and sys.maxsize > 2**32 and platform.machine().lower() in ('amd64','x86_64') else 1)" >nul 2>&1
if not errorlevel 1 set "mk300_python_tag=-3.11"
if not defined mk300_python_tag goto python_missing
:interpreter_ready
if exist ".venv-midi\Scripts\python.exe" goto check_environment
py %mk300_python_tag% -m venv .venv-midi
if errorlevel 1 goto failed
:check_environment
".venv-midi\Scripts\python.exe" -c "import sys,platform; print(sys.version); sys.exit(0 if sys.implementation.name == 'cpython' and sys.version_info[:2] in ((3,11),(3,12)) and sys.maxsize > 2**32 and platform.machine().lower() in ('amd64','x86_64') else 1)"
if errorlevel 1 goto incompatible_environment
echo Instalando pacotes prontos. Nenhuma compilacao C++ sera executada.
".venv-midi\Scripts\python.exe" -m pip install --only-binary=:all: "mido>=1.3,<2" "python-rtmidi==1.5.8"
if errorlevel 1 goto failed
".venv-midi\Scripts\python.exe" -c "import mido, rtmidi; print('Dependencias MIDI prontas.')"
if errorlevel 1 goto failed
echo Instalacao concluida. Conecte a MK-300 por USB, feche M-EFCS e abra testar.cmd.
pause
exit /b 0
:python_missing
echo Instale Python 3.12 x64 com o Python Launcher.
echo Download oficial: https://www.python.org/downloads/release/python-31210/
echo Escolha Windows installer 64-bit. Python 3.11 x64 tambem e aceito.
echo Depois execute este arquivo novamente. Nao precisa remover outros Pythons.
pause
exit /b 1
:incompatible_environment
echo O ambiente .venv-midi usa um Python incompativel.
echo Renomeie a pasta .venv-midi para .venv-midi-antiga e execute instalar.cmd novamente.
pause
exit /b 1
:failed
echo Falha na preparacao. Copie a mensagem acima para analisarmos.
echo O instalador exige pacotes binarios e nao tenta compilar.
pause
exit /b 1
