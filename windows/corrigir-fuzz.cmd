@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-midi\Scripts\python.exe" goto missing
echo Corrigir somente o fuzz do LITTLE WING na posicao 137. Feche M-EFCS.
".venv-midi\Scripts\python.exe" corrigir_fuzz.py --apply %*
set "mk300_fuzz_result=%errorlevel%"
pause
exit /b %mk300_fuzz_result%
:missing
echo Copie estes arquivos para sua pasta windows ja preparada.
pause
exit /b 1
