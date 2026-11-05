@echo off
setlocal EnableExtensions DisableDelayedExpansion
title MJON AI OS - Instalacion individual y reversible
chcp 65001 >nul
set "SOURCE=%~dp0MJON-AI-OS.exe"
set "MANIFEST=%~dp0SHA256-DESKTOP.txt"
set "DEST=%LOCALAPPDATA%\Programs\MJON AI OS"
set "START=%APPDATA%\Microsoft\Windows\Start Menu\Programs\MJON AI OS.lnk"
echo.
echo MJON AI OS Windows Desktop - instalador de usuario
echo No requiere administrador. No instala Windows, no toca TPM,
echo no activa servicios ni descarga modelos. Conserva tus archivos.
echo.
if not exist "%SOURCE%" (
 echo ERROR: Falta MJON-AI-OS.exe junto a este instalador.
 goto :fail
)
if not exist "%MANIFEST%" (
 echo ERROR: Falta SHA256-DESKTOP.txt.
 goto :fail
)
powershell.exe -NoProfile -NonInteractive -Command "$h=(Get-FileHash -LiteralPath '%SOURCE%' -Algorithm SHA256).Hash.ToLowerInvariant();$expected=Get-Content -LiteralPath '%MANIFEST%' -Raw;if(-not $expected.ToLowerInvariant().Contains($h+'  mjon-ai-os.exe')){exit 5}"
if errorlevel 1 (
 echo ERROR: El SHA256 del ejecutable no coincide con el paquete.
 goto :fail
)
echo.
choice /C SN /N /M "Instalar MJON AI OS solo para este usuario? [S/N] "
if errorlevel 2 (
 echo Instalacion cancelada.
 exit /b 0
)
if not exist "%DEST%" mkdir "%DEST%"
if errorlevel 1 goto :fail
copy /Y "%SOURCE%" "%DEST%\MJON-AI-OS.exe" >nul
if errorlevel 1 goto :fail
powershell.exe -NoProfile -NonInteractive -Command "$w=New-Object -ComObject WScript.Shell;$s=$w.CreateShortcut('%START%');$s.TargetPath='%DEST%\MJON-AI-OS.exe';$s.WorkingDirectory='%DEST%';$s.Description='MJON AI OS - Windows Desktop';$s.Save()"
if errorlevel 1 (
 echo La aplicacion se copio, pero Windows no pudo crear el acceso directo.
 echo Podes abrir "%DEST%\MJON-AI-OS.exe".
)
echo.
echo [OK] MJON AI OS copiado a "%DEST%"
echo Inicia desde el menu Inicio o desde la carpeta indicada.
echo No se configuraron inicios automaticos.
pause
exit /b 0
:fail
echo Instalacion NO completada. No se modifico la instalacion de Windows.
pause
exit /b 1
