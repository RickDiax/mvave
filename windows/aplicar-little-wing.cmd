@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-midi\Scripts\python.exe" goto missing
echo Little Wing - gravar somente na posicao 137.
echo Feche M-EFCS e DAW. Ctrl A/B serao preservados.
".venv-midi\Scripts\python.exe" little_wing.py --apply %*
set "mk300_lw_result=%errorlevel%"
echo.
echo Envie o JSON little_wing da pasta diagnosticos.
pause
exit /b %mk300_lw_result%
:missing
echo Copie estes arquivos para a pasta windows que ja contem .venv-midi.
pause
exit /b 1
