"""Opt-in Windows launcher; fixed executable allowlist, no shell."""
import subprocess
import sys
from .commands import interpret_command

_EXECUTABLES = {"notepad": "notepad.exe", "calc": "calc.exe", "explorer": "explorer.exe"}

def execute_spoken_command(text: str, *, confirmed: bool = False) -> str:
    action = interpret_command(text)
    if action is None:
        return "Orden no reconocida o no permitida."
    if not confirmed:
        return f"Confirmación necesaria: abrir {action[1]}."
    if sys.platform != "win32":
        return "Esta acción solo está disponible en Windows."
    subprocess.Popen([_EXECUTABLES[action[1]]], shell=False)
    return f"Abriendo {action[1]}."
