import ast
from pathlib import Path

import pytest

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "safety_layer"
SOURCES = sorted(SOURCE_ROOT.rglob("*.py"))

# Invariant 1 (no LLM or network calls) is enforced on imports by import-linter and
# ruff. Dynamic imports and code execution would get past both, so they are banned here.
FORBIDDEN_CALLS = {"__import__", "compile", "eval", "exec", "import_module"}


def _called_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                names.add(node.func.attr)
    return names


def test_sources_are_found() -> None:
    assert SOURCES, f"no Python sources under {SOURCE_ROOT}"


@pytest.mark.parametrize("path", SOURCES, ids=lambda path: path.name)
def test_source_has_no_dynamic_imports_or_code_execution(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    assert not _called_names(tree) & FORBIDDEN_CALLS
