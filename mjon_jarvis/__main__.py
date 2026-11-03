"""Interactive demo, separate from the Dodaios runtime."""
from .windows_actions import execute_spoken_command

def main() -> None:
    print("MJON JARVIS — demostración. Escribí salir para terminar.")
    while True:
        try:
            command = input("Orden: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nHasta luego.")
            return
        if command.casefold() in ("salir", "exit"):
            return
        response = execute_spoken_command(command)
        print(response)
        if response.startswith("Confirmación necesaria:"):
            if input("¿Confirmás? (si/no): ").strip().casefold() in ("si", "sí"):
                try:
                    print(execute_spoken_command(command, confirmed=True))
                except OSError as exc:
                    print(f"Windows no pudo abrir la aplicación: {exc}")

if __name__ == "__main__":
    main()
