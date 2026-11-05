@echo off
setlocal EnableExtensions DisableDelayedExpansion
title MJON AI OS - Desinstalar
chcp 65001 >nul
set "DEST=%LOCALAPPDATA%\Programs\MJON AI OS"
set "START=%APPDATA%\Microsoft\Windows\Start Menu\Programs\MJON AI OS.lnk"
echo.
echo Desinstalar la aplicacion MJON AI OS de este usuario?
echo No borra Windows, modelos IA, carpetas de usuario ni proyectos.
choice /C SN /N /M "Continuar? [S/N] "
if errorlevel 2 exit /b 0
if exist "%START%" del /Q "%START%"
if exist "%DEST%\MJON-AI-OS.exe" del /Q "%DEST%\MJON-AI-OS.exe"
echo [OK] Ejecutable y acceso directo retirados (si existian).
echo Otros archivos del usuario se conservaron.
pause
