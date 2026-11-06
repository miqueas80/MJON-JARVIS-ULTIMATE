"""MJON AI OS native, offline-first capability registry and routing policy.

A safe control plane, *not* a package installer or unconstrained agent executor.
No imports of optional engines, no subprocesses, downloads or network activity
are performed here. A detected binary is not proof of usable model weights.
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib.metadata
import shutil
from typing import Callable


@dataclass(frozen=True)
class ModuleSpec:
    module_id: str
    title: str
    domain: str
    executable: str = ""
    distribution: str = ""
    min_ram_gib: int = 4
    workstation_only: bool = False
    remote: bool = False
    engine_priority: int = 100
    auto_install: bool = False
    auto_start: bool = False
    install_policy: str = "opt_in"
    note: str = ""


def _cli(ident: str, title: str, domain: str, command: str, **kwargs) -> ModuleSpec:
    return ModuleSpec(ident, title, domain, executable=command, **kwargs)


def _py(ident: str, title: str, domain: str, distribution: str, **kwargs) -> ModuleSpec:
    return ModuleSpec(ident, title, domain, distribution=distribution, **kwargs)


# Policy minimums are intentionally CONSERVATIVE MJON guidance, not upstream
# package requirements or predictions of every possible model's memory use.
# No non-OS tool is auto-installed, auto-started, or granted privileges.
CATALOG: tuple[ModuleSpec, ...] = (
    # Hardware-aware inference. Only the first three are direct local chat
    # candidates; ONNX/OpenVINO are runtimes, not plug-and-play chat servers.
    _cli("llama_cpp", "llama.cpp / GGUF", "inference", "llama-cli", min_ram_gib=4, engine_priority=10),
    _cli("ollama", "Ollama", "inference", "ollama", min_ram_gib=6, engine_priority=20),
    _cli("localai", "LocalAI", "inference", "local-ai", min_ram_gib=16, workstation_only=True, engine_priority=30),
    _py("onnxruntime", "ONNX Runtime", "inference", "onnxruntime", min_ram_gib=4),
    _py("openvino", "OpenVINO", "inference", "openvino", min_ram_gib=8),
    _cli("vllm", "vLLM", "inference", "vllm", min_ram_gib=24, workstation_only=True),
    _cli("sglang", "SGLang", "inference", "sglang", min_ram_gib=24, workstation_only=True),
    _cli("free_llm_api", "Free LLM API (conector opcional)", "inference", "",
         remote=True, min_ram_gib=2, engine_priority=90, note="Requiere consentimiento, credenciales y verificación del proveedor."),
    # Agent orchestration. These require permissions and explicit opt-in.
    _cli("openclaw", "OpenClaw", "agents", "openclaw", min_ram_gib=8),
    _py("langgraph", "LangGraph", "agents", "langgraph", min_ram_gib=6),
    _py("crew_ai", "CrewAI", "agents", "crewai", min_ram_gib=8),
    _cli("goose", "Goose", "agents", "goose", min_ram_gib=8),
    ModuleSpec("agency_agents", "Agency Agents (perfiles)", "agents",
               min_ram_gib=4, note="Perfiles y definiciones: no es un ejecutor autónomo por sí solo."),
    _cli("openfang", "OpenFang", "agents", "openfang", min_ram_gib=8),
    _py("pydantic_ai", "PydanticAI", "agents", "pydantic-ai", min_ram_gib=4),
    # Programming
    _cli("opencode", "OpenCode", "programming", "opencode"),
    _cli("codex_cli", "Codex CLI", "programming", "codex", min_ram_gib=6),
    _cli("openhands", "OpenHands", "programming", "openhands", min_ram_gib=16, workstation_only=True),
    _cli("git", "Git", "programming", "git"),
    _cli("python", "Python", "programming", "python3"),
    _cli("rust", "Rust", "programming", "rustc"),
    _cli("nodejs", "Node.js", "programming", "node"),
    _cli("vscode_oss", "VS Code OSS", "programming", "code-oss", min_ram_gib=8),
    _cli("jupyter", "Jupyter", "programming", "jupyter", min_ram_gib=6),
    # Offline voice. Models and microphones must be tested separately.
    _cli("openvoiceos", "OpenVoiceOS", "voice", "ovos", min_ram_gib=8),
    _cli("whisper_cpp", "whisper.cpp", "voice", "whisper-cli", min_ram_gib=4),
    _py("sherpa_onnx", "sherpa-onnx", "voice", "sherpa-onnx", min_ram_gib=4),
    _cli("piper", "Piper TTS", "voice", "piper", min_ram_gib=4),
    _py("openwakeword", "openWakeWord", "voice", "openwakeword", min_ram_gib=4),
    # Vision
    _py("opencv", "OpenCV", "vision", "opencv-python", min_ram_gib=4),
    _py("paddleocr", "PaddleOCR", "vision", "paddleocr", min_ram_gib=8),
    _cli("tesseract", "Tesseract", "vision", "tesseract", min_ram_gib=4),
    _py("yolo", "Ultralytics YOLO", "vision", "ultralytics", min_ram_gib=8),
    _py("sam", "Segment Anything", "vision", "segment-anything", min_ram_gib=16, workstation_only=True),
    # Knowledge
    _cli("sqlite", "SQLite", "knowledge", "sqlite3", min_ram_gib=2),
    _py("faiss", "FAISS", "knowledge", "faiss-cpu", min_ram_gib=8),
    _cli("qdrant", "Qdrant", "knowledge", "qdrant", min_ram_gib=16, workstation_only=True),
    _py("llamaindex", "LlamaIndex", "knowledge", "llama-index", min_ram_gib=8),
    _py("docling", "Docling", "knowledge", "docling", min_ram_gib=8),
    # Automation
    _cli("mcp", "MCP", "automation", "mcp", min_ram_gib=4),
    _py("a2a", "A2A", "automation", "a2a-sdk", min_ram_gib=4),
    _cli("playwright", "Playwright", "automation", "playwright", min_ram_gib=8),
    _cli("nodered", "Node-RED", "automation", "node-red", min_ram_gib=8),
    # Multimedia & creative pipelines
    _cli("comfyui", "ComfyUI", "multimedia", "comfy", min_ram_gib=24, workstation_only=True),
    _py("diffusers", "Diffusers", "multimedia", "diffusers", min_ram_gib=16, workstation_only=True),
    _cli("blender", "Blender", "multimedia", "blender", min_ram_gib=8),
    _cli("ffmpeg", "FFmpeg", "multimedia", "ffmpeg", min_ram_gib=2),
    # Training: always explicitly optional on the 8 GiB laptop.
    _py("pytorch", "PyTorch", "training", "torch", min_ram_gib=16, workstation_only=True),
    _py("transformers", "Transformers", "training", "transformers", min_ram_gib=16, workstation_only=True),
    _py("peft", "PEFT", "training", "peft", min_ram_gib=16, workstation_only=True),
    _py("trl", "TRL", "training", "trl", min_ram_gib=16, workstation_only=True),
    _py("unsloth", "Unsloth", "training", "unsloth", min_ram_gib=24, workstation_only=True),
    _py("axolotl", "Axolotl", "training", "axolotl", min_ram_gib=24, workstation_only=True),
    # Performance & protection. MJON ANR code is external until audited.
    ModuleSpec("mjon_anr", "MJON ANR", "optimization",
               note="Motor propio aún no integrado: no inventar una instalación."),
    _cli("zram", "zram", "optimization", "zramctl", min_ram_gib=2),
    _cli("apparmor", "AppArmor", "security", "aa-status", min_ram_gib=2),
    _cli("podman", "Podman", "security", "podman", min_ram_gib=8),
    _cli("bubblewrap", "Bubblewrap", "security", "bwrap", min_ram_gib=4),
)


@dataclass(frozen=True)
class HardwareProfile:
    ram_gib: float
    discrete_gpu: bool
    network_available: bool = False


@dataclass(frozen=True)
class CapabilityPlan:
    capability: str
    engine_id: str | None
    reason: str
    remote: bool = False
    requires_approval: bool = False
    execute_automatically: bool = False


def _has_distribution(name: str) -> bool:
    try:
        importlib.metadata.version(name)
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


def _is_present(module: ModuleSpec,
                executable_exists: Callable[[str], bool],
                distribution_present: Callable[[str], bool]) -> bool:
    if module.remote:
        return False
    if module.executable:
        return executable_exists(module.executable)
    return bool(module.distribution and distribution_present(module.distribution))


def inspect_modules(
    *,
    executable_exists: Callable[[str], bool] | None = None,
    distribution_present: Callable[[str], bool] | None = None,
) -> list[dict[str, str | bool]]:
    """List on-device installations only; never claim model readiness."""
    checker = executable_exists or (lambda name: shutil.which(name) is not None)
    distributions = distribution_present or _has_distribution
    result = []
    for module in CATALOG:
        installed = _is_present(module, checker, distributions)
        status = ("remote_opt_in" if module.remote else
                  "installed_unverified" if installed else "not_installed")
        result.append({
            "id": module.module_id, "name": module.title,
            "domain": module.domain, "status": status,
            "launch": "manual_only", "offline": not module.remote,
            "workstation_only": module.workstation_only,
        })
    return result


def plan_capability(
    capability: str,
    hardware: HardwareProfile,
    *,
    executable_exists: Callable[[str], bool] | None = None,
    distribution_present: Callable[[str], bool] | None = None,
    allow_remote: bool = False,
    credentials_present: bool = False,
) -> CapabilityPlan:
    """Determine a safe candidate. Never installs, starts or invokes it.

    A candidate is NOT a ready model. The inference adapter checks for local
    model weights, a live service, and produces an explicit failure otherwise.
    """
    checker = executable_exists or (lambda name: shutil.which(name) is not None)
    distributions = distribution_present or _has_distribution
    candidates = sorted(
        (m for m in CATALOG if m.domain == capability and not m.remote),
        key=lambda m: (m.workstation_only, m.engine_priority, m.title),
    )
    for module in candidates:
        # A bare tensor runtime does not expose a chat server or an adapter.
        # Keep it visible in the catalog without selecting it as inference.
        if capability == "inference" and module.distribution and not module.executable:
            continue
        if module.min_ram_gib > hardware.ram_gib:
            continue
        if module.workstation_only and not hardware.discrete_gpu:
            continue
        if _is_present(module, checker, distributions):
            return CapabilityPlan(
                capability, module.module_id,
                "Motor detectado; verificar modelos, dependencias y permisos antes de usar.",
                requires_approval=capability in {"agents", "programming", "automation", "security"},
            )
    if capability == "inference" and hardware.network_available and allow_remote and credentials_present:
        return CapabilityPlan(
            capability, "free_llm_api", "Proveedor externo opcional, sujeto a consentimiento y límites.",
            remote=True, requires_approval=True,
        )
    return CapabilityPlan(
        capability, None, "No hay un motor local disponible y compatible; no se inicia ninguna alternativa.",
        requires_approval=capability in {"agents", "programming", "automation", "security"},
    )
