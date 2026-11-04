# MJON AI OS — Live USB experimental

Esta imagen es una **versión de prueba**, no la edición definitiva de MJON AI OS.

Incluye una distribución Debian 13 con KDE Plasma y el motor de JARVIS (fork de Dodaios) integrado. La imagen **no incluye un instalador del sistema operativo**, para priorizar pruebas no destructivas desde USB.

## Ecosistema nativo de IA — primera fase

Esta edición agrega la base del **Centro de mando unificado** de MJON AI OS:

- Interfaz gráfica con páginas de sistema, módulos IA, pruebas de IA local y seguridad.
- Los ajustes de redes, audio, Bluetooth, pantalla y energía se abren con los
  controles reales de KDE Plasma; sin requerir una terminal.
- Registro de motores y agentes de diversas familias, detectando instalaciones
  reales y distinguiendo ejecutables de pesos de modelos.
- Política de uso conservador en computadoras de 8 GiB: los entornos avanzados
  de entrenamiento/servidores GPU se mantienen opcionales y apagados.
- Un adaptador de prueba para Ollama local en `127.0.0.1:11434`. **No se incluye
  Ollama ni ningún modelo descargado**: si no existen, se indica que no hay
  motor local disponible en vez de generar respuestas falsas.
- Memoria comprimida zram y paquetes de seguridad base; todavía faltan perfiles
  de aislamiento de agentes auditados y persistencia USB.
- La conexión del nuevo plano de control con todas las conversaciones y
  herramientas de JARVIS sigue en desarrollo; no se anuncia como completa.

Esta es una **fase funcional de integración**, no la entrega de todas las
tecnologías opcionales enumeradas en la especificación.

## Corrección del segundo arranque en hardware

En una Conectar Igualdad real, KDE Plasma y la ventana MJON arrancaron,
pero la pantalla del asistente quedó en `Starting...`. El registro de
`mjon-jarvis.service` mostró
`ModuleNotFoundError: No module named 'dodaios.verse_host.relays'`.
La distribución Python original no incluía los módulos
`dodaios/verse_host/relays/*.py` en sus ruedas instalables porque
faltaba `dodaios/verse_host/relays/__init__.py`.

Esta generación corrige el paquete, comprueba todos esos módulos antes
de montar la imagen y ejecuta la importación real en el constructor de
Debian. La prueba física de esta corrección sigue pendiente hasta que
se inicie la ISO nueva en el equipo.

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
