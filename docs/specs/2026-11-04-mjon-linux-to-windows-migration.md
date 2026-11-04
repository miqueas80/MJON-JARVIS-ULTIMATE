# MJON AI OS — Evaluación de migración Linux → Windows (Fase 1)

**Fuente auditada:** `feature/mjon-ai-os-native`, commit `a1c34189daeff2ec25966a8a382366cdd40a9e2a`.

**Decisión:** migración **parcial/selectiva**, por componentes y pruebas. **No** copiar la distribución Debian ni alterar la UI Windows aprobada.

## Alcance comprobado previamente

La CI `MJON AI OS foundation`, ejecución `41862096695`, pasó en `windows-latest` y `ubuntu-latest` los contratos `mjon_os/tests` y generó el wheel en Ubuntu; **no** probó JARVIS+modelo local+micrófono+GPU de extremo a extremo en una computadora física Windows. La ISO `41862212906` validó un arranque Linux, no Windows. Ninguno de esos resultados demuestra que GTK/KDE se ejecuten en Windows.

## Matriz de decisión

| Función original | Decisión Windows | Razón |
|---|---|---|
| Catálogo y planificación de capacidades `mjon_os.ai_fabric` | Reutilizar con filtro de compatibilidad y alias | Lógica Python portable; la detección no equivale a modelo listo |
| Inferencia Ollama `mjon_os.local_inference` | Reutilizar con memoria Windows conocida, solo loopback | Protocolo HTTP local portable; sin caída automática a nube |
| JARVIS, comandos españoles y `open_app` | Reutilizar `mjon_jarvis` y el puente Dodaios | Ya tiene rutas Windows y controles de aprobación |
| Diagnósticos de RAM | Adaptar a `mjon_jarvis.system_status` en Windows | `/proc/meminfo` solo existe en Linux |
| Almacenamiento | Añadir comprobación de espacio y ruta por usuario | Evita repetir el agotamiento del overlay Live |
| Configuración del SO | Adaptador de URIs Microsoft `ms-settings:` con allowlist | No portar `/usr/bin/systemsettings` |
| Centro visual `mjon_os.ai_center` GTK/KDE | **Excluir** | Sustituir por la interfaz Windows que el usuario ya aprobó, sin rediseñarla |
| `live-build`, KDE, `systemd`, zram, AppArmor y Bubblewrap | **Excluir** | Funciones Linux-only; conservar límites/seguridad mediante APIs oficiales Windows |
| OpenVoiceOS, vLLM, SGLang, Unsloth y Axolotl | **No ofrecer como integraciones Windows de esta fase** | Compatibilidad nativa y recursos no demostrados |
| Entrenamiento, visión avanzada y múltiples agentes simultáneos | **Diferir** | Hardware de 8 GB; necesitarían pruebas de RAM, dependencias, licencias y seguridad |

Este producto Windows **no depende de ninguno de los otros proyectos personales**. El catálogo Windows excluye explícitamente `mjon_anr`.

## Entrega técnica de esta fase

`mjon_windows.backend` provee:
- Estado de instalaciones opcionales sin afirmaciones de funcionamiento falso.
- Selección conservadora de candidatos de motor según RAM, sin autoarranque ni llamada remota implícita.
- Apertura explícita de categorías de Windows Settings desde allowlist; ningún comando shell ni elevación.
- Diagnóstico no destructivo de sistema, disco y Ollama instalado; un ejecutable encontrado queda `installed_unverified`.
- Presupuesto de disco para modelo, archivos temporales y reserva, sin escritura ni borrado.
- Consulta Ollama únicamente en loopback y con RAM verificada; el servidor y el peso deben existir previamente.
- CLI `python -m mjon_windows --catalog|--doctor|--models|--ask|--settings`.

`mjon_windows` **no instala ni modifica Windows**, no implementa la interfaz visual, no incluye pesos GGUF, no configura voz, no asegura compatibilidad de GPU y no ejecuta agentes sin autorización.

## Pruebas y criterios de decisión

Suite `mjon_windows/tests/test_backend.py` (Windows/Ubuntu CI):
1. No listar como Windows funciones Linux-only.
2. Detectar aliases de ejecutables Windows.
3. Impedir fallback remoto no autorizado.
4. No activar motores automáticamente en 8 GB.
5. Permitir solo URIs Microsoft autorizadas, únicamente Windows.
6. No ofrecer descargas que consuman la reserva de disco.
7. Ruta persistente local por usuario sin crear directorios al inspeccionar.
8. Diagnóstico read-only sin `systemd` ni llamadas a nube.
9. No inferir si falta una medida fiable de RAM.
10. Enviar el modelo y presupuesto de RAM al adaptador Ollama.

La CI también ejecuta contratos de `ai_fabric`, `local_inference` y el puente de comandos españoles. Este documento no sustituye pruebas reales en Windows 11: faltan instalar ejecutables, modelos reales, verificar memoria/latencia, probar audio, accesibilidad, AppContainer/UAC y el comportamiento de la UI aprobada.

## Puertas para futuras migraciones

Antes de activar otra funcionalidad, exigir prueba reproducible en Windows nativo, consumo admisible en 8 GB, licencia revisada, mecanismo de permisos y desinstalación/recuperación. Las integraciones no verificadas permanecen opt-in o pendientes; nunca se anuncian como listas.

**Ramas:** base Linux sin cambios `feature/mjon-ai-os-native`; nueva rama de migración `feature/mjon-windows-migration`; `main` intacta.
