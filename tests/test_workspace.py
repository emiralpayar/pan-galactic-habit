"""Every workspace member must be covered by the checks CI requires.

Tool configuration lists paths explicitly, so a new member that is not added to
it would pass CI without being type-checked, tested, or held to an import contract.
"""

import tomllib
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> dict[str, Any]:
    with path.open("rb") as file:
        return tomllib.load(file)


CONFIG = _load(ROOT / "pyproject.toml")
MEMBERS: list[str] = CONFIG["tool"]["uv"]["workspace"]["members"]


def _package_name(member: str) -> str:
    project_name: str = _load(ROOT / member / "pyproject.toml")["project"]["name"]
    return project_name.replace("-", "_")


@pytest.mark.parametrize("member", MEMBERS)
def test_member_is_type_checked(member: str) -> None:
    mypy = CONFIG["tool"]["mypy"]
    assert f"{member}/src" in mypy["files"]
    assert f"{member}/tests" in mypy["files"]
    assert f"{member}/src" in mypy["mypy_path"]


@pytest.mark.parametrize("member", MEMBERS)
def test_member_is_tested(member: str) -> None:
    assert f"{member}/tests" in CONFIG["tool"]["pytest"]["ini_options"]["testpaths"]


@pytest.mark.parametrize("member", MEMBERS)
def test_member_is_held_to_an_import_contract(member: str) -> None:
    package = _package_name(member)
    importlinter = CONFIG["tool"]["importlinter"]
    assert package in importlinter["root_packages"]
    sources = {
        source for contract in importlinter["contracts"] for source in contract["source_modules"]
    }
    assert package in sources
