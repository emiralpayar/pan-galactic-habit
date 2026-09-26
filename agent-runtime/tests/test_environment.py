from pathlib import Path

import pytest

from agent_runtime import ClaudeConfig, CredentialError
from agent_runtime.claude import build_environment

CONFIG = ClaudeConfig(model="claude-sonnet-5")
CONFIG_DIR = Path("/tmp/config")  # noqa: S108 - never created; only its string is checked


def test_one_credential_is_passed_and_the_other_is_neutralized() -> None:
    env = build_environment({"CLAUDE_CODE_OAUTH_TOKEN": "tok"}, CONFIG, CONFIG_DIR)
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == "tok"  # noqa: S105
    assert env["ANTHROPIC_API_KEY"] == ""
    assert env["CLAUDE_CONFIG_DIR"] == str(CONFIG_DIR)


def test_no_credential_is_allowed_here_and_fails_when_the_cli_needs_one() -> None:
    env = build_environment({}, CONFIG, CONFIG_DIR)
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == ""
    assert env["ANTHROPIC_API_KEY"] == ""


def test_two_credentials_are_refused() -> None:
    parent = {"CLAUDE_CODE_OAUTH_TOKEN": "a", "ANTHROPIC_API_KEY": "b"}
    with pytest.raises(CredentialError, match="exactly one"):
        build_environment(parent, CONFIG, CONFIG_DIR)


@pytest.mark.parametrize(
    "name",
    [
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_CUSTOM_HEADERS",
        "ANTHROPIC_BEDROCK_BASE_URL",
        "HTTPS_PROXY",
        "NODE_OPTIONS",
        "NODE_TLS_REJECT_UNAUTHORIZED",
        "LD_PRELOAD",
        # Provider switches: the CLI checks all of these to pick an alternate backend.
        "CLAUDE_CODE_USE_BEDROCK",
        "CLAUDE_CODE_USE_VERTEX",
        "CLAUDE_CODE_USE_FOUNDRY",
        "CLAUDE_CODE_USE_MANTLE",
        "CLAUDE_CODE_USE_ANTHROPIC_AWS",
        "CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD",
        "CLAUDE_CODE_USE_GATEWAY",
        # The CLI runs on Bun, not Node: BUN_OPTIONS/BUN_CONFIG_FILE can load code into it.
        "BUN_OPTIONS",
        "BUN_CONFIG_FILE",
        # Other credential sources and certificate overrides the pinned CLI reads.
        "CLAUDE_CODE_OAUTH_REFRESH_TOKEN",
        "CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR",
        "CLAUDE_CODE_GATEWAY_TOKEN",
        "CLAUDE_CODE_SESSION_ACCESS_TOKEN",
        "CLAUDE_CODE_HOST_CREDS_FILE",
        "CLAUDE_CODE_CLIENT_CERT",
        "CLAUDE_CODE_HTTP_PROXY",
        "CLAUDE_CODE_CUSTOM_OAUTH_URL",
        # Set by a host Claude Code session; the contract test sets it aside, not the backend.
        "CLAUDE_CODE_MESSAGING_TOKEN",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK",
    ],
)
def test_unsupported_variables_are_refused(name: str) -> None:
    with pytest.raises(CredentialError, match=name):
        build_environment({name: "1"}, CONFIG, CONFIG_DIR)


def test_an_unnamed_endpoint_override_is_refused() -> None:
    with pytest.raises(CredentialError, match="ANTHROPIC_BASE_URL"):
        build_environment({"ANTHROPIC_BASE_URL": "https://proxy.example"}, CONFIG, CONFIG_DIR)


def test_an_endpoint_override_named_by_configuration_is_used() -> None:
    config = ClaudeConfig(model="m", base_url="https://proxy.example")
    parent = {"ANTHROPIC_BASE_URL": "https://proxy.example"}
    assert build_environment(parent, config, CONFIG_DIR)["ANTHROPIC_BASE_URL"] == config.base_url


def test_a_configured_endpoint_replaces_nothing_when_the_parent_sets_none() -> None:
    config = ClaudeConfig(model="m", base_url="https://proxy.example")
    assert build_environment({}, config, CONFIG_DIR)["ANTHROPIC_BASE_URL"] == config.base_url


def test_the_cli_is_kept_from_updating_itself() -> None:
    assert build_environment({}, CONFIG, CONFIG_DIR)["DISABLE_AUTOUPDATER"] == "1"


def test_empty_values_are_ignored() -> None:
    assert build_environment({"ANTHROPIC_MODEL": "", "HTTPS_PROXY": ""}, CONFIG, CONFIG_DIR)
