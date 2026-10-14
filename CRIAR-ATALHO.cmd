@echo off
setlocal
cd /d "%~dp0"
title MK300 Studio - Criar atalho
powershell.exe -NoProfile -Command "$ErrorActionPreference='Stop'; $root=(Get-Location).Path; $shell=New-Object -ComObject WScript.Shell; $destinations=@([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'),'MK300 Studio.lnk'),[IO.Path]::Combine($root,'MK300 Studio.lnk')); foreach($path in $destinations){$link=$shell.CreateShortcut($path); $link.TargetPath=[IO.Path]::Combine($root,'ABRIR-STUDIO.cmd'); $link.WorkingDirectory=$root; $link.IconLocation=[IO.Path]::Combine($root,'studio','assets','mk300-studio.ico'); $link.Description='MK300 Studio - Timbres do ChatGPT para sua pedaleira'; $link.Save()}"
if errorlevel 1 (
  echo Nao foi possivel criar o atalho. Use ABRIR-STUDIO.cmd para abrir o Studio.
  pause
  exit /b 1
)
echo Atalhos MK300 Studio criados nesta pasta e na Area de Trabalho.
echo Mantenha esta pasta no mesmo local para os atalhos continuarem funcionando.
pause
