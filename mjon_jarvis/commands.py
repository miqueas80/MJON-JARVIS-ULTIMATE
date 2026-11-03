"""Small deterministic Spanish Windows command interpreter; never executes commands."""
import re
import unicodedata

_TARGETS = {"bloc de notas": "notepad", "notas": "notepad", "calculadora": "calc", "explorador de archivos": "explorer", "explorador": "explorer"}

def _normalize(text: str) -> str:
    text = "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))
    return " ".join(text.strip().split())

def interpret_command(text: str) -> tuple[str, str] | None:
    if not isinstance(text, str) or len(text) > 256:
        return None
    normalized = _normalize(text)
    normalized = re.sub(r"^jarvis\s*[,;:]\s*|^jarvis\s+", "", normalized)
    match = re.fullmatch(r"(abre|abrir|abri)\s+(?:el |la )?(.+)", normalized)
    if not match:
        return None
    target = _TARGETS.get(match.group(2))
    return ("launch", target) if target else None
