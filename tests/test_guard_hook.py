"""The Claude Code guard hook allows PR merges and approvals only into agent-main.

Only a loop agent account may merge or approve, and only for a pull request into
agent-main (ADR 0010). The GitHub rulesets are the boundary; this hook is the
guardrail in front of them. Every command below is only fed to the hook as JSON;
nothing runs it.
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
GIT = shutil.which("git") or "/usr/bin/git"

# A stand-in for gh: PR 7 targets agent-main, every other PR targets main, and the
# signed-in account is FAKE_GH_LOGIN.
FAKE_GH = """#!/usr/bin/env bash
if [ "$1 $2" = "pr view" ]; then
  case "$3" in 7|*/pull/7) echo agent-main ;; *) echo main ;; esac
elif [ "$1 $2" = "api user" ]; then
  echo "$FAKE_GH_LOGIN"
fi
"""

URL = "https://github.com/emiralpayar/pan-galactic-habit/pull"
AGENT = "emiralpayar-agent"
OWNER = "MGokcay"


def _git(repo: Path, *args: str) -> None:
    subprocess.run([GIT, "-C", str(repo), *args], check=True, capture_output=True)  # noqa: S603


@pytest.fixture(scope="module")
def fake_bin(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("bin")
    gh = directory / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    return directory


@pytest.fixture(scope="module")
def repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A repository on a work branch whose origin/main names the maintainers as code owners."""
    path = tmp_path_factory.mktemp("repo")
    _git(path, "init", "-q", "-b", "feat/1-work")
    (path / ".github").mkdir()
    (path / ".github" / "CODEOWNERS").write_text("*  @emiralpayar @mgokcay\n")
    _git(path, "add", ".")
    _git(path, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "init")
    _git(path, "update-ref", "refs/remotes/origin/main", "HEAD")
    return path


def _allowed(command: str, fake_bin: Path, repo: Path, login: str = AGENT) -> bool:
    payload = json.dumps({"tool_input": {"command": command}, "cwd": str(repo)})
    env = {
        **os.environ,
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        "FAKE_GH_LOGIN": login,
    }
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
        "gh api repos/o/r/pulls/43",
        "git push -u origin feat/45-agents-merge-cross-reviewed-prs",
    ],
)
def test_allowed(command: str, fake_bin: Path, repo: Path) -> None:
    assert _allowed(command, fake_bin, repo)


@pytest.mark.parametrize(
    "command",
    [
        # Into main.
        "gh pr merge 43 --squash",
        "gh pr review 43 --approve --body-file review.md",
        "gh pr review 43 --approve=true --body-file x",
        "gh pr review 43 -ab LGTM",
        'gh pr review 43 "--approve" -b x',
        'gh pr "merge" 43 --squash',
        "gh pr mer''ge 43",
        "gh pr m\\erge 43",
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
        "gh pr review 7 -ab LGTM",
        "gh pr review 7 --approve=true",
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
        "gh alias set mm 'pr merge'",
        "gh extension install someone/gh-merge",
        "gh auth token",
        "curl -X PUT https://api.github.com/repos/o/r/pulls/43/merge",
        # The same operations through the API, or by retargeting a PR.
        "gh api -X PUT repos/o/r/pulls/43/merge",
        'gh api -X PUT repos/o/r/pulls/43/"merge"',
        "gh api -X PUT repos/o/r/pulls/43/me''rge",
        "gh api graphql -f query=mutation{enablePullRequestAutoMerge}",
        "gh api graphql -F query=@q.graphql",
        "gh api repos/o/r/pulls/43/reviews -f event=APPROVE",
        "gh api repos/o/r/pulls/43/revi''ews -f event=APPROVE",
        "gh api -X PATCH repos/o/r/pulls/7 -f base=main",
        "gh pr edit 7 --base main",
        "gh pr edit 7 -B main",
        "gh pr edit 7 -Bmain",
        'gh pr edit 7 "--base" main',
        # Pushing to a protected branch.
        "git push origin main",
        "git push origin agent-main",
        "git push origin 'agent-main'",
        "git push origin HEAD:agent-main",
        "git push --all origin",
        "git push --mirror origin",
    ],
)
def test_blocked(command: str, fake_bin: Path, repo: Path) -> None:
    assert not _allowed(command, fake_bin, repo)


@pytest.mark.parametrize("login", [OWNER, "emiralpayar"])
@pytest.mark.parametrize(
    "command", ["gh pr merge 7 --squash", "gh pr review 7 --approve --body-file review.md"]
)
def test_a_code_owner_account_cannot_merge_or_approve(
    command: str, login: str, fake_bin: Path, repo: Path
) -> None:
    assert not _allowed(command, fake_bin, repo, login=login)
