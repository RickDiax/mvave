@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-midi\Scripts\python.exe" goto missing
echo Copia autorizada: Belief 142 para USER PRESET 137, com nome TESTE USB.
echo Feche M-EFCS e DAW. A posicao 137 sera conferida antes de salvar.
".venv-midi\Scripts\python.exe" copiar_teste.py --apply %*
set "mk300_copy_result=%errorlevel%"
echo.
echo Envie o JSON copia_142_137 da pasta diagnosticos.
pause
exit /b %mk300_copy_result%
:missing
echo Execute instalar.cmd primeiro ou copie estes arquivos para a pasta windows ja preparada.
pause
exit /b 1
