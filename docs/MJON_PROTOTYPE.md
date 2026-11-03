# MJON JARVIS — primer prototipo ejecutable

Este módulo es opt-in y está separado del runtime de Dodaios por ahora. No reemplaza el motor de voz ni el agente existente.

En Windows con Python 3.11+ desde la raíz del repositorio:

```powershell
python -m mjon_jarvis
```

Órdenes admitidas: `Jarvis, abrí el bloc de notas`, `abrir calculadora`, `abrí explorador de archivos`.

Cada apertura requiere confirmación. No ejecuta scripts ni PowerShell arbitrario.

Pruebas focalizadas:

```powershell
python -m unittest discover -s tests -p 'test_mjon_*.py'
```

La integración con voz, interfaz y permisos de Dodaios requiere auditar sus módulos. No representa aún control completo del escritorio.
