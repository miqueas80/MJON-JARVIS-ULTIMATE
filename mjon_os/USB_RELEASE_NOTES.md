# MJON AI OS — Live USB experimental

Esta imagen es una **versión de prueba**, no la edición definitiva de MJON AI OS.

Incluye una distribución Debian 13 con KDE Plasma y el motor de JARVIS (fork de Dodaios) integrado. La imagen **no incluye un instalador del sistema operativo**, para priorizar pruebas no destructivas desde USB.

## Mejoras verificadas para esta generación

- Corrección del usuario `user` de Debian Live y comprobación real de su contraseña mediante PAM.
- Inicio automático de una sola sesión KDE Plasma para evitar solicitar credenciales cada vez que arranca el pendrive.
- Puerta de publicación más estricta: el mismo USB debe iniciar Linux, autenticar al usuario Live, abrir Plasma, mantener el servicio JARVIS activo y responder en `http://127.0.0.1:47821/api/health` en máquinas virtuales BIOS y UEFI.
- Conservación del entorno Live sin instalador, manteniendo intactas las particiones de Windows durante el arranque normal.

**No se garantiza que toda aplicación, micrófono, aceleración gráfica o modelo de IA funcione en todos los equipos.** El objetivo de esta entrega es validar el sistema operativo y la integración nativa en hardware real. Algunas funciones avanzadas de IA y voz siguen sujetas a configuración y modelos instalados.

Si usás **Ventoy**, copiá esta ISO nueva al espacio de archivos del pendrive y elegila en el menú de Ventoy; **no hace falta formatear otra vez el USB**. Asegurate de seleccionar la ISO cuyo nombre corresponde a la versión recién descargada y no el archivo anterior.

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
