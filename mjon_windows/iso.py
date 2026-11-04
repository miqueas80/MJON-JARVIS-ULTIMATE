"""Build a VERIFIED, NON-BOOTABLE ISO containing the Windows MJON tools.

This is distribution media for a Windows application. It is NOT a Windows
installer ISO, does not contain licensed Microsoft OS files, does not replace
or install Windows, and does not claim the frozen visual shell is implemented.

Optional build-only dependency: pycdlib >= 1.14.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any


_README = """MJON AI OS - Herramientas Windows (vista previa)
================================================
NO ES BOOTEABLE. NO INSTALA NI REEMPLAZA WINDOWS.

Esta ISO contiene herramientas de MJON para ejecutar DENTRO de Windows.
Necesitas tener Windows ya instalado y una sesion autorizada.

CONTENIDO
- MJON-Windows-Tools.exe: diagnosticos de Windows, catalogo de motores,
  consulta de Ollama local e interfaz con Configuracion del sistema.
- LEEME.txt: este documento.
- SHA256SUMS.txt: SHA256 para validar el ejecutable.
- LICENSE.txt y NOTICE.txt: atribuciones y licencias originales.

COMO UTILIZARLA
1. En Windows 10/11 x64, hace doble clic sobre el archivo .iso para montarlo.
2. Copia MJON-Windows-Tools.exe a una carpeta de tu usuario.
3. Abri PowerShell en esa carpeta.
4. Ejecuta .\\MJON-Windows-Tools.exe --doctor
5. Ejecuta .\\MJON-Windows-Tools.exe --catalog
6. Si ya tenes Ollama instalado con un modelo descargado:
   .\\MJON-Windows-Tools.exe --models
   .\\MJON-Windows-Tools.exe --ask "Hola" --model "nombre:etiqueta"

FUNCIONES QUE TODAVIA NO INCLUYE
- No es una instalacion de Windows ni imagen arrancable por Ventoy.
- No contiene la interfaz grafica aprobada ni la altera.
- No instala Ollama, modelos, controladores ni Windows automaticamente.
- No garantiza reconocimiento de voz ni integracion de todos los agentes.
- El ejecutable no esta firmado digitalmente.

No se ejecuta ningun instalador automaticamente al montar la ISO.
Conserva copias de tus datos y utiliza un entorno de pruebas para experimentar.
"""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_distribution(
    executable: Path,
    iso_path: Path,
    *,
    license_file: Path,
    notice_file: Path,
) -> dict[str, Any]:
    """Create ISO9660/Joliet data ISO with an intact executable and attribution.

    No boot catalog or Windows WIM is added. Content includes a direct, easily
    audited SHA256 manifest; an external build must smoke-test the .exe first.
    """
    import pycdlib

    executable, iso_path = Path(executable), Path(iso_path)
    license_file, notice_file = Path(license_file), Path(notice_file)
    for path in (executable, license_file, notice_file):
        if not path.is_file():
            raise FileNotFoundError(f"Archivo requerido inexistente: {path}")
    if executable.suffix.lower() != ".exe":
        raise ValueError("Se requiere un ejecutable Windows .exe verificado.")
    if iso_path.resolve() in {executable.resolve(), license_file.resolve(), notice_file.resolve()}:
        raise ValueError("La salida ISO no puede sobrescribir los archivos de origen.")

    checksum = _sha256(executable)
    iso_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as root:
        tmp = Path(root)
        readme = tmp / "LEEME.txt"
        readme.write_text(_README, encoding="utf-8")
        hashes = tmp / "SHA256SUMS.txt"
        hashes.write_text(f"{checksum}  MJON-Windows-Tools.exe\n", encoding="ascii")

        media = pycdlib.PyCdlib()
        media.new(interchange_level=3, joliet=3, vol_ident="MJON_WIN_TOOLS")
        try:
            entries = [
                (executable, "/MJON.EXE;1", "/MJON-Windows-Tools.exe"),
                (readme, "/LEEME.TXT;1", "/LEEME.txt"),
                (hashes, "/SHA256.TXT;1", "/SHA256SUMS.txt"),
                (license_file, "/LICENSE.TXT;1", "/LICENSE.txt"),
                (notice_file, "/NOTICE.TXT;1", "/NOTICE.txt"),
            ]
            for source, iso_name, joliet_name in entries:
                media.add_file(str(source), iso_path=iso_name, joliet_path=joliet_name)
            media.write(str(iso_path))
        finally:
            media.close()
    manifest = {
        "product": "MJON AI OS Windows Tools",
        "channel": "preview",
        "bootable": False,
        "windows_included": False,
        "graphical_shell_included": False,
        "executable": executable.name,
        "executable_sha256": checksum,
        "iso_sha256": _sha256(iso_path),
        "iso_size_bytes": iso_path.stat().st_size,
    }
    (iso_path.parent / (iso_path.name + ".json")).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (iso_path.parent / "SHA256SUMS.txt").write_text(
        f"{manifest['iso_sha256']}  {iso_path.name}\n"
        f"{checksum}  {executable.name}\n", encoding="ascii"
    )
    return manifest


def verify_distribution(iso_path: Path, executable: Path) -> None:
    """Read actual bytes back out of ISO; fail if archive corrupt or differs."""
    import pycdlib
    import hashlib

    iso = pycdlib.PyCdlib()
    iso.open(str(iso_path))
    try:
        with tempfile.TemporaryFile() as extracted:
            iso.get_file_from_iso_fp(extracted, iso_path="/MJON.EXE;1")
            extracted.seek(0)
            digest = hashlib.sha256()
            for chunk in iter(lambda: extracted.read(1024 * 1024), b""):
                digest.update(chunk)
            if digest.hexdigest() != _sha256(Path(executable)):
                raise RuntimeError("SHA256 del ejecutable extraido de la ISO no coincide.")
        for name in ("/LEEME.TXT;1", "/SHA256.TXT;1", "/LICENSE.TXT;1", "/NOTICE.TXT;1"):
            iso.get_record(iso_path=name)
    finally:
        iso.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build nonbootable MJON Windows tools ISO")
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--license", type=Path, required=True)
    parser.add_argument("--notice", type=Path, required=True)
    args = parser.parse_args(argv)
    result = make_distribution(
        args.exe, args.iso, license_file=args.license, notice_file=args.notice
    )
    verify_distribution(args.iso, args.exe)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
