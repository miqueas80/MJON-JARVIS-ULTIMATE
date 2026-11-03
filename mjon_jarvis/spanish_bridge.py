"""Conservative Spanish desktop intent parser for the Dodaios action router.

Only produces plans. Execution and authorization remain with Dodaios.
All supported application identifiers already belong to Dodaios' open_app tool.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import re
import unicodedata


@dataclass(frozen=True, slots=True)
class SpanishDesktopRequest:
    kind: str  # launch | computer_use
    app: str | None = None


_APPLICATIONS = {
    "bloc de notas": "notepad",
    "notas": "notepad",
    "notepad": "notepad",
    "calculadora": "calc",
    "calc": "calc",
    "explorador de archivos": "explorer",
    "explorador": "explorer",
    "explorer": "explorer",
    "terminal de windows": "wt",
    "windows terminal": "wt",
    "terminal": "wt",
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "spotify": "spotify",
    "discord": "discord",
    "whatsapp": "whatsapp",
}
# The native OS uses KDE; Windows executable aliases are not valid there.
# Do not change upstream non-native installations or perform execution here.
_NATIVE_KDE_APPS = {
    "bloc de notas": "kate", "notas": "kate", "notepad": "kate",
    "calculadora": "kcalc", "calc": "kcalc",
    "explorador de archivos": "dolphin", "explorador": "dolphin", "explorer": "dolphin",
    "terminal": "konsole", "terminal de windows": "konsole", "windows terminal": "konsole",
}
_OPEN_RE = re.compile(r"^(?:abre|abri|abrir|inicia)\s+(?P<target>.+)$")
_GUI_RE = re.compile(
    r"^(?:(?:hace|haz|da)\s+(?:clic|click)\s+|"
    r"(?:clickea|cliquea|pulsa|presiona|selecciona|arrastra)\s+|"
    r"(?:escribi|escribe)\s+.+\s+en\s+(?:el|la|un|una)\s+(?:campo|ventana|cuadro|chat)\b)"
)
_NEGATION_RE = re.compile(r"\b(?:no|nunca|jamas)\b")
_QUESTION_RE = re.compile(r"^(?:como|que|cuando|donde|por que|cual|puedo|podria|podrias)\b")
_PROJECT_RE = re.compile(r"\b(?:pull request|pr|repositorio|github|gitlab|issue|rama|branch|proyecto)\b")
_COMPOUND_RE = re.compile(r"\s+(?:y|luego|despues)\s+", re.IGNORECASE)


def _prepare(text: str) -> str:
    if not isinstance(text, str) or not text or len(text) > 512:
        return ""
    folded = "".join(
        char for char in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(char)
    )
    normalized = " ".join(folded.strip().lstrip("¿¡").split())
    normalized = re.sub(r"^(?:hey\s+)?jarvis\s*[,;:\-]?\s*", "", normalized)
    return normalized.strip().rstrip(".?! ")


def _open_target(command: str) -> str | None:
    if _NEGATION_RE.search(command) or _QUESTION_RE.match(command) or ";" in command:
        return None
    match = _OPEN_RE.fullmatch(command)
    if match is None:
        return None
    return match.group("target")


def is_spanish_open_intent(text: str) -> bool:
    """Prevents open-app requests from being force-spawned as coding workers."""
    target = _open_target(_prepare(text))
    if target is None:
        return False
    first = _COMPOUND_RE.split(target, maxsplit=1)[0]
    return not bool(_PROJECT_RE.search(first))


def parse_spanish_request(text: str) -> SpanishDesktopRequest | None:
    """Classify supported desktop commands without executing any operation."""
    command = _prepare(text)
    if not command or _NEGATION_RE.search(command) or _QUESTION_RE.match(command) or ";" in command:
        return None

    target = _open_target(command)
    if target is not None:
        parts = _COMPOUND_RE.split(target, maxsplit=1)
        name = parts[0].strip().rstrip(",.!")
        name = re.sub(r"^(?:el|la|los|las|un|una)\s+", "", name)
        name = re.sub(r"\s+por favor$", "", name)
        app = _APPLICATIONS.get(name)
        if os.environ.get("MJON_NATIVE_OS") == "1":
            app = _NATIVE_KDE_APPS.get(name, app)
        if app is None:
            return None
        return SpanishDesktopRequest("computer_use") if len(parts) > 1 else SpanishDesktopRequest("launch", app)

    if _GUI_RE.match(command):
        return SpanishDesktopRequest("computer_use")
    return None
