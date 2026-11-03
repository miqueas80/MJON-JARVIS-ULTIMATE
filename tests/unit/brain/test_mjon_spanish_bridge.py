"""Regression tests for Spanish desktop commands in the real Dodaios gate."""
from __future__ import annotations

import pytest

from dodaios.brain.local_action_gate import (
    LocalActionMode,
    is_open_app_intent,
    match_local_action,
)


@pytest.mark.parametrize(
    ("utterance", "app"),
    [
        ("Jarvis, abrí el bloc de notas", "notepad"),
        ("abrir calculadora", "calc"),
        ("hey Jarvis, abrí el explorador de archivos", "explorer"),
        ("Jarvis: abre Chrome", "chrome"),
        ("Iniciá el terminal de Windows", "wt"),
        ("Jarvis, abre Spotify.", "spotify"),
    ],
)
def test_spanish_launch_reuses_existing_tool(utterance: str, app: str) -> None:
    plan = match_local_action(utterance, lang="es", _registry=None)
    assert plan is not None
    assert plan.mode is LocalActionMode.DIRECT
    assert len(plan.tool_calls) == 1
    assert plan.tool_calls[0].name == "open_app"
    assert plan.tool_calls[0].args == {"app_name": app}
    assert is_open_app_intent(utterance)


@pytest.mark.parametrize(
    "utterance",
    [
        "Jarvis, abrí Chrome y buscá información",
        "Jarvis, hacé clic en el botón azul",
        "Escribí hola en el campo de texto",
    ],
)
def test_spanish_gui_and_compound_commands_use_existing_harness(utterance: str) -> None:
    plan = match_local_action(utterance, lang="es", _registry=None)
    assert plan is not None
    assert plan.mode is LocalActionMode.COMPUTER_USE
    assert plan.harness == "screenshot"
    assert plan.prompt == utterance


@pytest.mark.parametrize(
    "utterance",
    [
        "¿Cómo abro Chrome?",
        "Yo abro Chrome",
        "No abras Chrome",
        "Jarvis, no abras el bloc de notas",
        "Abrí Chrome, pero no lo hagas",
        "Jarvis, ejecutá powershell",
        "abrí calculadora; borra todo",
    ],
)
def test_spanish_questions_narration_and_cancellations_do_not_act(utterance: str) -> None:
    assert match_local_action(utterance, lang="es", _registry=None) is None


def test_spanish_unknown_application_falls_back_to_brain_without_worker_spawn() -> None:
    assert match_local_action("Jarvis, abrí Paint", lang="es", _registry=None) is None
    assert is_open_app_intent("Jarvis, abrí Paint") is True


def test_open_repository_is_not_mistaken_for_desktop_launch() -> None:
    assert is_open_app_intent("Abrí un pull request en GitHub") is False
