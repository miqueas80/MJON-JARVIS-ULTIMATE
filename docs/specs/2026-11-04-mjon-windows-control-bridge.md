# MJON AI OS Windows — Contrato de controles sin cambios visuales

Estado: integración del backend de controles, **no** producto listo para instalar.
Rama: `feature/mjon-windows-migration`. Fuente Linux original: `a1c34189daeff2ec25966a8a382366cdd40a9e2a`.

## Invariantes del producto

- El fondo orbital, la navegación, las barras y las pantallas aprobadas por el usuario quedan **congelados**.
- No se mezclan otros proyectos o productos personales con MJON AI OS.
- No se copia GTK, KDE, Debian Live, `systemd`, zram, AppArmor ni comandos administrativos de Linux.
- `main` y `feature/mjon-ai-os-native` no se modifican.
- Se mantiene JARVIS/Dodaios con atribuciones y política de permisos originales.
- Ningún comando detectado implica que un modelo ya sea funcional; ninguna nube se utiliza como fallback implícito.

## Conexión con el servidor existente

El servidor FastAPI de JARVIS incluye el router de `mjon_windows.routes` únicamente si:

1. Se ejecuta en Windows real: `sys.platform == "win32"`.
2. El proceso ha iniciado en modo edición MJON: `MJON_WINDOWS_EDITION=1`.

No se monta en Linux ni altera el comportamiento predeterminado de Dodaios en Windows. Los GET se sirven bajo la protección de seguridad de superficie ya existente. Las acciones POST exigen origen de navegador loopback, con host y puerto idénticos, y no aceptan encabezados Bearer de agentes o CLI. Esta condición **no sustituye** las verificaciones de permisos del sistema operativo ni protege de un proceso local malicioso bajo el mismo usuario.

## API de controles funcionales

| Endpoint | Tipo | Uso real | Side effects |
|---|---|---|---|
| `GET /api/mjon/windows/overview` | lectura | diagnóstico Windows real + módulos detectados | ninguno |
| `GET /api/mjon/windows/models` | lectura | consulta Ollama en `127.0.0.1:11434` | llamada local; no genera |
| `POST /api/mjon/windows/models/test` | acción aprobada | intenta **una generación real** del modelo pedido | consume RAM/CPU; sin nube |
| `POST /api/mjon/windows/settings/open` | acción aprobada | abre la categoría Microsoft Settings permitida | abre la ventana de Windows |
| `POST /api/mjon/windows/storage/check` | lectura activada por usuario | estima si el volumen real tiene espacio suficiente para un modelo y margen reservado | ninguno; nunca inicia descarga |

La petición al control de almacenamiento solo acepta `model_bytes`: el volumen libre es medido por el backend, no se acepta ni se confía en un número enviado por el navegador. El control de modelos diferencia `server_reachable`, `models_available`, `generation_tested` y `ready`. La disponibilidad de pesos no convierte `ready` en true; solo el resultado de una generación real reporta `generation_tested=true`.

El módulo TypeScript `dodaios/ui/web/frontend/src/lib/mjonWindowsBridge.ts` ofrece tipos y funciones para enlazar controles sin alterar CSS, estructura de componentes o imágenes. **No hay todavía una nueva pantalla visual MJON programada.**

## Pruebas

La CI `.github/workflows/mjon-windows-migration.yml` verifica en Windows y Linux:
- Contratos Python del backend, detección y política offline.
- Endpoints FastAPI con TestClient, bloqueo de orígenes no confiables y Bearer, respuesta degradada sin Ollama, y presupuesto de espacio real.
- Contratos heredados de `mjon_os.ai_fabric`, `mjon_os.local_inference` y comandos españoles de JARVIS.
- Lectura de memoria y disco en Windows real de runner GitHub Actions.
- Pruebas de TypeScript/Vitest del cliente API, sin tocar la UI.

Estas pruebas no equivalen a una prueba funcional con un modelo descargado real; para declarar **IA local lista** se exige también una generación comprobada con peso cuantizado en una máquina Windows de destino.

## Próximas puertas

1. Prueba real Ollama/llama.cpp con un modelo pequeño en Windows 11, con latencia/RAM y cancelación.
2. Vincular los componentes de la interfaz **previamente aprobada** al puente, sin recrear fondos.
3. Diagnósticos de micrófono, altavoces y pantalla con APIs nativas y permisos.
4. Instalación, respaldo y recuperación de datos de usuario sin intervenir la instalación Windows principal.
5. Pruebas físicas en CPU Intel/8 GB RAM y verificación visual contra las pantallas aprobadas, antes de publicar un instalador.

No anunciar que hay un modelo offline operativo, una shell Windows terminada ni una imagen instalable hasta completar esas puertas.
