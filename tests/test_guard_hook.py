"""The Claude Code guard hook allows PR merges and approvals only into agent-main.

The development loop runs on the maintainers' own accounts, which are code owners,
so for main this hook is the control that stops a loop session from approving or
merging (ADR 0010). Every command below is only fed to the hook; nothing runs it.
"""

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "guard-git.sh"
BASH = shutil.which("bash") or "/bin/bash"

# A stand-in for gh: PR 7 targets agent-main, every other PR targets main.
FAKE_GH = """#!/usr/bin/env bash
if [ "$1 $2" = "pr view" ]; then
  case "$3" in 7|*/pull/7) echo agent-main ;; *) echo main ;; esac
fi
"""

URL = "https://github.com/emiralpayar/pan-galactic-habit/pull"


@pytest.fixture(scope="module")
def fake_bin(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("bin")
    gh = directory / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    return directory


def _allowed(command: str, fake_bin: Path) -> bool:
    payload = json.dumps({"tool_input": {"command": command}, "cwd": str(ROOT)})
    env = {**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"}
    # The command only reaches the hook as JSON on stdin; the process run is our own hook.
    result = subprocess.run(  # noqa: S603
        [BASH, str(HOOK)], input=payload, capture_output=True, text=True, env=env, check=False
    )
    assert result.returncode in (0, 2), result.stderr
    return result.returncode == 0


@pytest.mark.parametrize(
    "command",
    [
        "gh pr merge 7 --squash",
        "gh pr merge 7 --merge",
        f"gh pr merge {URL}/7 --squash",
        "gh pr review 7 --approve --body-file review.md",
        "gh pr review 43 --comment --body-file review.md",
        "gh pr review 43 --request-changes --body-file review.md",
        "gh pr view 43",
        "gh pr edit 7 --add-label needs-human",
        "gh api repos/o/r/pulls/43/reviews --jq .",
        "git push -u origin feat/45-agents-merge-cross-reviewed-prs",
    ],
)
def test_allowed(command: str, fake_bin: Path) -> None:
    assert _allowed(command, fake_bin)


@pytest.mark.parametrize(
    "command",
    [
        # Into main.
        "gh pr merge 43 --squash",
        "gh pr review 43 --approve --body-file review.md",
        # No PR named, or not by number or URL.
        "gh pr merge --squash",
        "gh pr merge feat/x --squash",
        "gh pr merge https://github.com/other/repo/pull/7 --squash",
        # Options the loop does not need.
        "gh pr merge 7 --admin --squash",
        "gh pr merge 7 --squash --auto",
        "gh pr merge 7 -R other/repo",
        "gh pr merge 7 --squash -Rother/repo",
        "gh pr merge 7 --squash '--admin'",
        'gh pr merge 7 --squash "-R" other/repo',
        "gh pr review 7 --approve --body-file --admin",
        # A second command hidden behind the allowed one.
        "gh pr merge 7 --squash && gh pr merge 43 --squash",
        "gh pr merge 7 --squash; gh pr merge 43",
        "gh pr merge 7 --squash\ngh pr merge 43 --squash",
        "gh pr review 7 --approve --body-file x\ngh pr review 43 --approve --body-file x",
        "gh pr review 7 --approve\ngh api -X PUT repos/o/r/pulls/43/merge",
        "echo x\ngh pr merge 43",
        "gh pr merge $(echo 43) --squash",
        # Other ways to reach gh.
        "GH_REPO=o/r gh pr merge 43 --squash",
        "command gh pr merge 43 --squash",
        "env gh pr merge 43",
        "/usr/local/bin/gh pr merge 43",
        # The same operations through the API, or by retargeting a PR.
        "gh api -X PUT repos/o/r/pulls/43/merge",
        "gh api graphql -f query=mutation{enablePullRequestAutoMerge}",
        "gh api repos/o/r/pulls/43/reviews -f event=APPROVE",
        "gh pr edit 7 --base main",
        "gh pr edit 7 -B main",
        # Pushing to a protected branch.
        "git push origin main",
        "git push origin agent-main",
        "git push origin 'agent-main'",
        "git push origin HEAD:agent-main",
        "git push --all origin",
        "git push --mirror origin",
    ],
)
def test_blocked(command: str, fake_bin: Path) -> None:
    assert not _allowed(command, fake_bin)
