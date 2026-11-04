# MJON AI OS — construcción de ISO Windows 11 (preparación reproducible)

**Estado:** constructor y verificación previa. **NO** existe aún una ISO completa de MJON AI OS Windows Edition ni una implementación ejecutable de las pantallas visuales aprobadas. El diseño permanece congelado.

## Decisión: construcción local o runner propio, no GitHub estándar

El trabajo con una ISO oficial de 8 GB requiere mantener el archivo original, su copia extraída, la salida final y espacio temporal. Los runners estándar de Windows en GitHub tienen aproximadamente 14 GB de disco; el cálculo preventivo de este proyecto exige alrededor de 30 GB para una fuente de 8 GiB y el manual recomienda **35 GB libres o más**. No conviene subir 8 GB al chat ni al repositorio.

La ISO oficial es del usuario, obtenida de Microsoft. No se almacena ni se publica una copia de Windows en este repositorio o en GitHub Releases. No hay claves ni mecanismos para alterar requisitos de Windows.

## Qué sí está listo

- Constructor: `packaging/windows/build-mjon-win11-media.ps1`
- Comprobaciones de fuentes y espacio: `mjon_windows/media_policy.py`
- Pruebas: `mjon_windows/tests/test_media_policy.py`
- Validación CI y opción runner propio: `.github/workflows/mjon-windows-iso-builder.yml`
- Herramienta MJON compilada disponible en la entrega previa, archivo `MJON-Windows-Tools.exe`, con `SHA256SUMS.txt`.

El constructor verifica hash SHA-256 de la fuente, firma válida de Microsoft en `setup.exe`, archivos de instalación y arranque, capacidad libre, integridad de MJON y presencia de Windows ADK `oscdimg.exe`. Reutiliza los sectores de arranque originales UEFI+BIOS, crea la ISO y vuelve a montarla para verificar la copia del ejecutable. **No ejecuta ni instala MJON durante el proceso de instalación de Windows**.

## Requisitos

1. Windows 10/11 x64 en el equipo de construcción, con **35 GB libres** en la unidad de salida.
2. Una ISO x64 oficial de Windows 11, descargada desde https://www.microsoft.com/es-es/software-download/windows11 .
3. Windows ADK de Microsoft, componente **Deployment Tools**, que proporciona `oscdimg.exe`. Instrucciones: https://learn.microsoft.com/en-us/windows-hardware/get-started/adk-install .
4. Paquete de herramientas MJON extraído del ZIP aprobado en la CI anterior, con **`MJON-Windows-Tools.exe` y `SHA256SUMS.txt`**.
5. Licencia legítima de Windows apropiada para el equipo. La ISO modificada no activa Windows.

## Uso local (sin subir la ISO a ChatGPT ni GitHub)

Abrí PowerShell y creá una carpeta de salida, por ejemplo `D:\MJON\out`. Suponiendo:

- ISO oficial en `D:\ISO\Windows11.iso`
- Herramientas MJON en `D:\MJON\package`
- Salida deseada en `D:\MJON\out\MJON-Win11-Integration-Preview.iso`

Calculá el hash de la fuente con:

```powershell
Get-FileHash -Algorithm SHA256 'D:\ISO\Windows11.iso'
```

Si Microsoft publica un hash de referencia para esa edición, contrastalo con el valor obtenido. En el repositorio, abrí PowerShell en la raíz y ejecutá primero la validación (reemplazando la cadena de SHA256 con el resultado real):

```powershell
pwsh -NoProfile -File packaging/windows/build-mjon-win11-media.ps1 -WindowsIso 'D:\ISO\Windows11.iso' -ExpectedWindowsSha256 'TU_SHA256_DE_64_CARACTERES' -PayloadDirectory 'D:\MJON\package' -OutputIso 'D:\MJON\out\MJON-Win11-Integration-Preview.iso' -PreflightOnly
```

Si pasa, ejecutá el mismo comando **sin `-PreflightOnly`**. El constructor no sobrescribe el original. Verificá el hash resultante en consola y probá la ISO **primero en una VM UEFI**. Ninguna prueba automatizada de preflight sustituye una instalación real.

## GitHub Actions

La CI sobre `windows-latest` solo ejecuta pruebas de seguridad y análisis sintáctico del constructor. No descarga imágenes Windows.

La construcción completa está preparada como tarea manual **optativa** para un runner propio con etiquetas `self-hosted, windows, x64, mjon-iso-builder` y 35 GB libres. Para habilitarla se requieren:

- Secretos de repositorio `MJON_WINDOWS_ISO_PATH`, `MJON_WINDOWS_ISO_SHA256` (ruta y SHA256 de la ISO ya presente en ese runner).
- Variables `MJON_PAYLOAD_PATH`, `MJON_OUTPUT_PATH`, `MJON_BUILDER_READY=true`.
- Ejecutar la acción con `build_preview_iso=true` desde una versión del workflow disponible en la rama principal de GitHub. **Actualmente la rama principal no se modifica**; por ello el camino inmediato es ejecutar el script localmente.

No existe un artefacto GitHub Actions público con el ISO modificado. El archivo generado se conserva **en el equipo del usuario**. Esto evita redistribuir el medio de instalación de Windows sin autorización.

## Qué queda antes de llamarlo ISO MJON AI OS completa

- Programar el escritorio Windows visualmente aprobado. No hay todavía fuente de UI ejecutable que represente fielmente las imágenes aprobadas.
- Conectar el núcleo de JARVIS con los controles reales de esa UI y probar respuesta, ajustes, voz, permisos y agentes.
- Construir un instalador propio de MJON con rollback y consentimiento, e integrarlo correctamente al proceso postinstalación de Windows.
- Ejecutar pruebas reales de instalación Windows UEFI y en hardware Intel con 8 GB, drivers, almacenamiento y compatibilidad, sin saltarse TPM/Secure Boot.
- Revisar licencias, autorizaciones de redistribución y método de entrega. La ISO oficial de Microsoft y su licencia nunca están incluidas automáticamente en este repositorio.

**Conclusión:** se puede generar una **ISO booteable de instalación de Windows con herramientas MJON opcionales** cuando el usuario aporte su medio original localmente. Eso es un paso de integración y no equivale todavía al sistema MJON AI OS Windows Edition terminado.
