@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-midi\Scripts\python.exe" goto missing
echo Teste de leitura MK-300 V75. Nenhum preset sera alterado.
".venv-midi\Scripts\python.exe" diagnostico.py --firmware V75 %*
set "mk300_test_result=%errorlevel%"
echo.
echo Envie o arquivo JSON da pasta diagnosticos para analisarmos.
pause
exit /b %mk300_test_result%
:missing
echo Execute instalar.cmd primeiro.
pause
exit /b 1
