@echo off
setlocal EnableExtensions DisableDelayedExpansion
title MJON AI OS Windows - Generar ISO con escritorio
chcp 65001 >nul
if /I "%~1"=="--self-test" (
 echo MJON_ISO_DESKTOP_SCRIPT_OK
 exit /b 0
)
set "ROOT=C:\MJON"
set "ISO=%USERPROFILE%\Downloads\Windows11_Client_x64_es-es_26300_9457.iso"
set "HASH=9828703784880421E6602504DFD99064E4CB739CC9B20ABA22E3934372A14F9A"
set "SOURCE=%ROOT%\Windows11-x64"
set "TOOLS=%ROOT%\package"
set "DESKTOP=%~dp0"
set "OUTDIR=%ROOT%\out"
set "OUTPUT=%OUTDIR%\MJON-Win11-Desktop-Preview.iso"
set "ADK=C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg\oscdimg.exe"
set "SEVENZIP=C:\Program Files\7-Zip\7z.exe"
set "WORK=%ROOT%\stage-MJON-DESKTOP-%RANDOM%-%RANDOM%"
set "ORDER=%WORK%-boot-order.txt"
echo.
echo ==========================================================
echo   MJON AI OS - Nueva ISO Windows x64 con escritorio MJON
echo ==========================================================
echo El proceso NO instala Windows ni cambia tu sistema actual.
echo La ISO es de integracion; NO es un Windows final verificado.
echo.
if not exist "%SOURCE%\sources\install.wim" if not exist "%SOURCE%\sources\install.esd" (
 echo ERROR: Falta install.wim o install.esd en los archivos de Windows.
 goto :fail
)
if not exist "%SOURCE%\setup.exe" (
 echo ERROR: No existe setup.exe en Windows extraido.
 goto :fail
)
if not exist "%SOURCE%\sources\boot.wim" (
 echo ERROR: Falta boot.wim.
 goto :fail
)
if not exist "%SOURCE%\boot\etfsboot.com" (
 echo ERROR: Falta arranque BIOS.
 goto :fail
)
if not exist "%SOURCE%\efi\microsoft\boot\efisys.bin" (
 echo ERROR: Falta arranque UEFI.
 goto :fail
)
if not exist "%ISO%" (
 echo ERROR: No se encontro la ISO de Windows oficial.
 goto :fail
)
if not exist "%TOOLS%\MJON-Windows-Tools.exe" (
 echo ERROR: Falta la herramienta de diagnostico MJON anterior.
 goto :fail
)
if not exist "%TOOLS%\SHA256SUMS.txt" (
 echo ERROR: Falta el manifest SHA256 de herramientas MJON.
 goto :fail
)
if not exist "%DESKTOP%MJON-AI-OS.exe" (
 echo ERROR: Extrae el ZIP del escritorio junto a este CMD.
 goto :fail
)
if not exist "%DESKTOP%SHA256-DESKTOP.txt" (
 echo ERROR: Falta SHA256-DESKTOP.txt del nuevo escritorio.
 goto :fail
)
if not exist "%DESKTOP%INSTALAR-MJON.cmd" (
 echo ERROR: Falta INSTALAR-MJON.cmd.
 goto :fail
)
if not exist "%DESKTOP%DESINSTALAR-MJON.cmd" (
 echo ERROR: Falta DESINSTALAR-MJON.cmd.
 goto :fail
)
if not exist "%ADK%" (
 echo ERROR: No se encontro oscdimg.exe (Windows ADK).
 goto :fail
)
if not exist "%SEVENZIP%" (
 echo ERROR: Falta 7-Zip en Program Files.
 goto :fail
)
if exist "%OUTPUT%" (
 echo ERROR: La ISO destino YA existe. No se sobrescribe.
 echo %OUTPUT%
 goto :fail
)
echo [1/7] Verificando origen Microsoft y SHA-256...
powershell.exe -NoProfile -NonInteractive -Command "if((Get-FileHash -LiteralPath '%ISO%' -Algorithm SHA256).Hash -ne '%HASH%'){exit 7}"
if errorlevel 1 (
 echo ERROR: SHA256 de Windows incorrecto.
 goto :fail
)
powershell.exe -NoProfile -NonInteractive -Command "$s=Get-AuthenticodeSignature -LiteralPath '%SOURCE%\setup.exe';if($s.Status -ne 'Valid' -or -not $s.SignerCertificate -or $s.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation'){exit 7}"
if errorlevel 1 (
 echo ERROR: Firma Microsoft de setup.exe no valida.
 goto :fail
)
echo [2/7] Verificando hashes de MJON...
powershell.exe -NoProfile -NonInteractive -Command "$h=(Get-FileHash -LiteralPath '%DESKTOP%MJON-AI-OS.exe' -Algorithm SHA256).Hash.ToLowerInvariant();$m=(Get-Content -LiteralPath '%DESKTOP%SHA256-DESKTOP.txt' -Raw).ToLowerInvariant();if(-not $m.Contains($h+'  mjon-ai-os.exe')){exit 8}"
if errorlevel 1 (
 echo ERROR: SHA256 de MJON-AI-OS.exe no coincide.
 goto :fail
)
powershell.exe -NoProfile -NonInteractive -Command "$h=(Get-FileHash -LiteralPath '%TOOLS%\MJON-Windows-Tools.exe' -Algorithm SHA256).Hash.ToLowerInvariant();$m=(Get-Content -LiteralPath '%TOOLS%\SHA256SUMS.txt' -Raw).ToLowerInvariant();if(-not $m.Contains($h+'  mjon-windows-tools.exe')){exit 8}"
if errorlevel 1 (
 echo ERROR: SHA256 de MJON-Windows-Tools.exe no coincide.
 goto :fail
)
echo [3/7] Comprobando 35 GB libres en C...
powershell.exe -NoProfile -NonInteractive -Command "$d=Get-PSDrive -Name C;if($d.Free -lt 35GB){exit 3}"
if errorlevel 1 (
 echo ERROR: Necesitamos al menos 35 GB libres en C.
 goto :fail
)
if not exist "%OUTDIR%" mkdir "%OUTDIR%"
if errorlevel 1 goto :fail
mkdir "%WORK%"
if errorlevel 1 goto :fail
echo [4/7] Copiando Windows en un directorio temporal...
robocopy "%SOURCE%" "%WORK%" /E /COPY:DAT /DCOPY:DAT /R:2 /W:1 /NFL /NDL /NJH /NJS
if errorlevel 8 (
 echo ERROR: No se pudo copiar Windows.
 goto :fail
)
echo [5/7] Anadiendo escritorio, herramientas e instalacion reversible...
mkdir "%WORK%\MJON"
if errorlevel 1 goto :fail
copy /Y "%DESKTOP%MJON-AI-OS.exe" "%WORK%\MJON\" >nul
if errorlevel 1 goto :fail
copy /Y "%DESKTOP%SHA256-DESKTOP.txt" "%WORK%\MJON\" >nul
if errorlevel 1 goto :fail
copy /Y "%DESKTOP%INSTALAR-MJON.cmd" "%WORK%\MJON\" >nul
if errorlevel 1 goto :fail
copy /Y "%DESKTOP%DESINSTALAR-MJON.cmd" "%WORK%\MJON\" >nul
if errorlevel 1 goto :fail
copy /Y "%TOOLS%\MJON-Windows-Tools.exe" "%WORK%\MJON\" >nul
if errorlevel 1 goto :fail
copy /Y "%TOOLS%\SHA256SUMS.txt" "%WORK%\MJON\" >nul
if errorlevel 1 goto :fail
(
 echo MJON AI OS Windows Desktop - vista previa de integracion.
 echo Windows 11 requiere licencia original y hardware compatible.
 echo Esta ISO NO se ha validado arrancando en un equipo o VM.
 echo Despues de instalar Windows, abre la carpeta MJON del medio.
 echo Ejecuta INSTALAR-MJON.cmd solo si queres instalar la app.
 echo Ese instalador requiere consentimiento y no inicia servicios.
 echo El escritorio MJON permite JARVIS local, modelos, diagnostico,
 echo y accesos a configuracion sin cambios automaticos.
 echo No incluye modelos IA predescargados ni un Windows modificado.
 echo Verifica el SHA256 antes de ejecutar los EXE.
) > "%WORK%\MJON\LEEME-MJON.txt"
(for %%F in (boot\bcd boot\boot.sdi boot\etfsboot.com efi\microsoft\boot\bcd efi\boot\bootx64.efi efi\microsoft\boot\efisys.bin sources\boot.wim) do @if exist "%WORK%\%%F" echo %%F) > "%ORDER%"
echo [6/7] Generando ISO con oscdimg de Microsoft...
"%ADK%" -m -o -u2 -udfver102 -lMJON_WIN11_X64 "-bootdata:2#p0,e,b%WORK%\boot\etfsboot.com#pEF,e,b%WORK%\efi\microsoft\boot\efisys.bin" "-yo%ORDER%" "%WORK%" "%OUTPUT%"
if errorlevel 1 (
 echo ERROR: oscdimg no pudo terminar la ISO.
 goto :fail
)
if not exist "%OUTPUT%" (
 echo ERROR: No se creo la ISO.
 goto :fail
)
echo [7/7] Verificando presencia del escritorio en la ISO...
"%SEVENZIP%" l -slt "%OUTPUT%" > "%WORK%-contents.txt"
if errorlevel 1 goto :fail
findstr /i /c:"Path = MJON\MJON-AI-OS.exe" "%WORK%-contents.txt" >nul
if errorlevel 1 (
 echo ERROR: La ISO no contiene el ejecutable MJON.
 goto :fail
)
echo.
echo [OK] ISO de integracion con escritorio creada:
echo %OUTPUT%
echo.
echo SHA256 final:
certutil -hashfile "%OUTPUT%" SHA256
echo.
echo NO instales esta ISO aun sin probarla en una VM UEFI.
echo Los archivos de Windows original se conservaron.
echo.
pause
exit /b 0
:fail
echo.
echo [ERROR] Construccion interrumpida o ISO no verificada.
echo No se modifico la instalacion Windows actual.
echo Si el archivo de salida existe tras un fallo, consideralo INVALIDO.
echo.
pause
exit /b 1
