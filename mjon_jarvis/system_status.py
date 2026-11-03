"""Windows system status with bounded, non-shell subprocess calls."""
from dataclasses import dataclass
import platform
import subprocess


@dataclass(frozen=True)
class SystemStatus:
    os_name: str
    release: str
    architecture: str
    memory_total_bytes: int | None


def parse_total_memory(output: str) -> int | None:
    """Parse PowerShell integer-only memory result without evaluating it."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if len(lines) != 1 or not lines[0].isascii() or not lines[0].isdecimal():
        return None
    value = int(lines[0])
    return value if 0 < value < 2**64 else None


def read_status(*, runner=subprocess.run, os_name=None) -> SystemStatus:
    current_os = os_name if os_name is not None else platform.system()
    total = None
    if current_os == "Windows":
        try:
            result = runner(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                 "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"],
                capture_output=True, text=True, timeout=5, check=False,
                shell=False,
            )
            if result.returncode == 0:
                total = parse_total_memory(result.stdout)
        except (OSError, subprocess.TimeoutExpired):
            pass
    return SystemStatus(current_os, platform.release(), platform.machine(), total)
