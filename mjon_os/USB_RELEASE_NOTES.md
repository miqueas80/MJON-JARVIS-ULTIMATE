# MJON AI OS — Live USB experimental

Esta imagen es una **versión de prueba**, no la edición definitiva de MJON AI OS.

Incluye una distribución Debian 13 con KDE Plasma y el motor de JARVIS (fork de Dodaios) integrado. La imagen **no incluye un instalador del sistema operativo**, para priorizar pruebas no destructivas desde USB.

## Descargar y comprobar

Descargá el archivo `MJON-AI-OS-dev-amd64.iso` y el archivo de verificación `.iso.sha256` que aparecen debajo de esta descripción. Conservá ambos en la misma carpeta y verificá el SHA-256 antes de grabar la imagen.

En PowerShell:

```powershell
(Get-FileHash .\MJON-AI-OS-dev-amd64.iso -Algorithm SHA256).Hash
```

El resultado debe coincidir con los 64 caracteres hexadecimales del archivo `.iso.sha256` adjunto. Si no coincide, **no utilices la imagen**.

## Llevarla al USB

Utilizá una memoria USB vacía de **al menos 8 GB**. Grabá la **imagen ISO completa**, sin descomprimirla, con una herramienta confiable para escribir imágenes de Linux, como USBImager o balenaEtcher. **Se borrarán los archivos del USB**; comprobá muy bien que elegiste el dispositivo removible y no el disco interno de Windows.

Desde el menú temporal de arranque de la computadora, seleccioná el USB y probá la sesión Live. No modifiques particiones ni formatees el disco de Windows.

Una vez en KDE, abrí Konsole y escribí:

```bash
mjon-doctor --json
```

Para conocer errores de JARVIS:

```bash
systemctl --user status mjon-jarvis.service --no-pager
```

## Limitaciones previstas

- La imagen se considera apta para una **prueba de hardware**, no para uso de producción.
- Una prueba de arranque en máquina virtual no garantiza que Wi-Fi, audio o gráficos funcionen en todas las laptops.
- La IA local avanzada puede necesitar modelos no incluidos; no se garantiza razonamiento sin Internet.
- Para volver a Windows, apagá el sistema, sacá el USB y encendé la computadora normalmente.

MJON AI OS es un proyecto independiente basado en Debian GNU/Linux y código abierto Dodaios; no está afiliado al equipo de Dodaios. Se conservan las licencias y atribuciones del proyecto original.
