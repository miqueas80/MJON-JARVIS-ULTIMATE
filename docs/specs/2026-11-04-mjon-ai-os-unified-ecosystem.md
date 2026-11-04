# MJON AI OS — Ecosistema Unificado de Inteligencia Artificial
**Especificación v1 · 2026-11-04 · Un solo repositorio**

Repositorio: `miqueas80/MJON-JARVIS-ULTIMATE`. Rama experimental:
`feature/mjon-ai-os-native`. Base: Debian 13 Live amd64 + KDE Plasma.

## Visión

MJON AI OS es un producto integrado: una sesión gráfica del sistema, un agente
central supervisado (JARVIS), un plano de control de capacidades y ejecutores
adaptados al hardware. No es un menú de descargas que lanza 60 programas
simultáneamente.

El acceso visible es `MJON AI OS - Centro de mando`; su sección Sistema abre
los paneles reales de KDE y su sección Módulos IA muestra un catálogo
consultado sobre el hardware real. La pestaña IA local usa Ollama por loopback,
si el usuario ya lo instaló y descargó modelos. Ninguna llamada a la nube
se realiza como alternativa implícita.

## Mapa de responsabilidades

```text
KDE Plasma / panel MJON              JARVIS (único asistente de sesión)
          |                                      |
          +----------------+---------------------+
                           |
                mjon_os.ai_fabric
          detección + catálogo + política de recursos
                           |
     +---------------------+----------------------------+
     |                     |                            |
 Motor local           Agentes supervisados       APIs remotas opcionales
 llama.cpp/Ollama       OpenClaw/Graph/...         Free LLM API y similares
 (opt-in y pesos)       (opt-in, sandbox)          (opt-in con credenciales)
```

**Importante:** el plano de control ya puede seleccionar un motor candidato
con política offline-first y probar Ollama mediante su API local.
Esto NO significa que JARVIS ya envíe todas sus conversaciones por este
coordinador; esa integración completa está pendiente, y no se anuncia como
funcional antes de una prueba real de extremo a extremo.

## Contratos arquitectónicos

1. **Un sistema, una sesión de JARVIS:** conserva el servicio de usuario
   `mjon-jarvis.service` y el control de permisos original.
2. **Sin root por defecto:** los módulos no reciben privilegios de sistema
   automáticamente. Acciones sobre cuentas, archivos, red, instalación,
   dispositivos y dinero requieren aprobación explícita.
3. **Motores heterogéneos:** adaptar una capacidad con interfaz común
   (chat local, STT, TTS, visión, recuperación, herramientas), no empotrar
   dependencias de GPU dentro de la ISO universal.
4. **Estado veraz:** detectar un ejecutable no demuestra que un servidor
   responda ni que existan pesos de modelos locales.
5. **Offline real, pero específico:** KDE, documentación local, inventario,
   diagnósticos y enrutamiento funcionan offline; la generación de texto solo
   cuando haya un motor local y pesos presentes.
6. **Persistencia explícita:** en Live USB sin partición persistente los datos,
   instalaciones y modelos pueden perderse al reiniciar. No prometer memoria
   de largo plazo hasta habilitar almacenamiento seguro de usuario.
7. **Límites de hardware:** sobre 8 GiB de RAM la política prefiere
   llama.cpp/GGUF u Ollama para modelos chicos. El entrenamiento completo,
   servidores vLLM/SGLang grandes y ComfyUI no arrancan automáticamente.
8. **Seguridad verificable:** AppArmor y Bubblewrap deben ser comprobados
   con perfiles concretos; instalarlos solamente NO significa que los agentes
   ya estén aislados. No habilitar `Bypass permissions` por defecto.
9. **Derechos y procedencia:** auditar licencias, pesos, descargadores y
   marcas de cada módulo antes de empaquetar; conservar licencia y NOTICE de
   Dodaios, no atribuir aprobación de terceros.
10. **Actualizaciones y rollback:** cada ISO lleva SHA256, commit de origen,
    pruebas de BIOS/UEFI y notas de cambios. Revertir al USB anterior sin
    particionar la unidad Windows.

## Perfiles

| Perfil | Hardware | Qué se carga |
|---|---|---|
| Live escolar | 8 GiB RAM, Intel iGPU | KDE, JARVIS, GTK Centro, zram, AI fabric; motores opcionales inactivos |
| Local asistido | 8–16 GiB y memoria persistente | 1 motor local cuantizado a la vez, STT/TTS livianos bajo demanda |
| Workstation | 24+ GiB y GPU compatible | Servicios vLLM/SGLang, visión y entrenamiento según VRAM real |
| Servidor | Hardware dedicado, red y perfiles estrictos | Multiagente y workers aislados con métricas y auditoría |

Los umbrales son criterios conservadores de MJON, **no garantías**
de rendimiento o requisitos universales de los proyectos upstream.

## Fases y puerta de verificación

- **Fase A (base existente):** Debian Live, KDE, usuarios, Wi-Fi/firmware,
  JARVIS, configuraciones, ISO BIOS/UEFI. Ya hubo pruebas físicas que
  detectaron y permitieron corregir errores de login y packaging.
- **Fase B (en construcción):** Centro de mando, catálogo y política
  de módulos, adaptador local Ollama, zram y servicios base. Tests Windows,
  Linux, rueda Python, ISO y VM obligatorios.
- **Fase C:** convertir los planes de capacidades en acciones aprobadas
  usando Action Registry de JARVIS; integrar un motor local CPU realmente
  distribuible, probar modelo con y sin Internet y mediciones RSS/latencia.
- **Fase D:** voz offline completa, wake word, herramientas de visión,
  memoria persistente con backups, MCP/A2A y agentes aislados.
- **Fase E:** perfiles GPU, Tauri cuando aporte valor, entrenamiento/
  multimedia opcionales, actualizaciones gráficas, auditoría de licencia
  y pruebas físicas de varias computadoras.

**Criterio para llamar a la ISO "final":** se arranca en BIOS/UEFI y en
la Conectar Igualdad física; Wi-Fi RTL8822CE, audio, micrófono, permisos,
inicio de JARVIS, consulta con modelo local offline, persistencia,
controles de seguridad y recuperación se prueban con evidencia.
No hay objetivo porcentual subjetivo ni promesa de cero errores.

## Referencias técnicas

- Debian live-build y Debian 13 Live.
- vLLM: https://docs.vllm.ai/en/latest/getting_started/installation/gpu/
- SGLang: https://docs.sglang.ai/
- systemd zram-generator: https://github.com/systemd/zram-generator
- Seguridad del sistema base: AppArmor, Podman y Bubblewrap oficiales.

