from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "01_onboarding_eda.ipynb"
REPORT = ROOT / "env_report.json"

ANSWER_PLACEHOLDER = "*(odpowiedź)*"
NONE_ASSIGNMENT = re.compile(r"(?m)^\s*[A-Za-z_][A-Za-z0-9_]*\s*=\s*None\s*$")


def load_notebook() -> dict:
    assert NOTEBOOK.exists(), f"Brakuje notebooka: {NOTEBOOK.relative_to(ROOT)}"
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


def executable_lines(source: str) -> list[str]:
    return [
        line
        for line in source.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def test_environment_report_exists_and_is_ok() -> None:
    assert REPORT.exists(), (
        "Brakuje env_report.json. Uruchom: python scripts/check_env.py"
    )

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report.get("status") == "ok", (
        "env_report.json nie ma statusu 'ok'. Uruchom ponownie check_env.py "
        "i popraw zgłoszone problemy."
    )
    assert report.get("python", {}).get("ok") is True, "Raport nie potwierdza Pythona 3.11.x."
    assert report.get("environment", {}).get("ok") is True, "Raport nie potwierdza środowiska asi-ml."


def test_all_required_markdown_answers_are_filled() -> None:
    notebook = load_notebook()
    remaining: list[int] = []

    for index, cell in enumerate(notebook.get("cells", []), start=1):
        if cell.get("cell_type") != "markdown":
            continue
        source = "".join(cell.get("source", []))
        if any(line.strip() == ANSWER_PLACEHOLDER for line in source.splitlines()):
            remaining.append(index)

    assert not remaining, (
        "W notebooku zostały nieuzupełnione pola *(odpowiedź)* w komórkach: "
        + ", ".join(map(str, remaining))
    )


def test_required_code_todos_contain_code() -> None:
    notebook = load_notebook()
    empty_todos: list[int] = []

    for index, cell in enumerate(notebook.get("cells", []), start=1):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        required_todo = "# TODO:" in source
        optional_todo = "# TODO (opcjonalnie)" in source
        if required_todo and not optional_todo and not executable_lines(source):
            empty_todos.append(index)

    assert not empty_todos, (
        "Wymagane komórki TODO nie zawierają kodu: "
        + ", ".join(map(str, empty_todos))
    )


def test_required_choices_are_not_left_as_none() -> None:
    notebook = load_notebook()
    unresolved: list[int] = []

    for index, cell in enumerate(notebook.get("cells", []), start=1):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        if NONE_ASSIGNMENT.search(source):
            unresolved.append(index)

    assert not unresolved, (
        "W notebooku zostały obowiązkowe wybory ustawione na None w komórkach: "
        + ", ".join(map(str, unresolved))
    )
