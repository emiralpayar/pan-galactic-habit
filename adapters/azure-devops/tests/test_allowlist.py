from collections.abc import AsyncIterator

import httpx
import pytest
from pydantic import SecretStr

from azure_devops.allowlist import ALLOWLIST, AllowlistTransport, RequestNotAllowedError, operations
from azure_devops.config import AzureDevOpsConfig

CONFIG = AzureDevOpsConfig(
    organization="contoso", project="Sandbox", token=SecretStr("not-a-real-token")
)
ALLOWED = f"{CONFIG.base_url}_apis/wit/workitems?ids=1&api-version=7.1"


def _transport() -> AllowlistTransport:
    return AllowlistTransport(
        httpx.MockTransport(lambda request: httpx.Response(200)),
        base_path=CONFIG.base_path,
        allowed=operations("read"),
    )


def _check(url: str, method: str = "GET", **kwargs: object) -> None:
    _transport().check(httpx.Request(method, url, **kwargs))  # type: ignore[arg-type]


def test_an_allowlisted_request_passes() -> None:
    _check(ALLOWED)


def test_every_listed_operation_is_read_only_for_now() -> None:
    # The write request builder is a separate, `loosens` change (ADR 0005).
    assert {request.kind for request in ALLOWLIST} == {"read"}
    assert operations("write") == ()


@pytest.mark.parametrize(
    ("url", "reason"),
    [
        pytest.param(ALLOWED.replace("https://", "http://"), "not dev.azure.com", id="http"),
        pytest.param(
            ALLOWED.replace("dev.azure.com", "dev.azure.com.evil.test"), "not dev", id="host"
        ),
        pytest.param(ALLOWED.replace("dev.azure.com", "dev.azure.com:8443"), "not dev", id="port"),
        pytest.param(
            ALLOWED.replace("https://", "https://user:pw@"), "do not belong", id="userinfo"
        ),
        pytest.param(ALLOWED + "#fragment", "do not belong", id="fragment"),
        pytest.param(ALLOWED.replace("/contoso/", "/other-org/"), "outside", id="other-org"),
        pytest.param(ALLOWED.replace("/Sandbox/", "/Other/"), "outside", id="other-project"),
        pytest.param(
            ALLOWED.replace("_apis/wit/workitems", "_apis/wit/workitems/1"),
            "not an allowlisted request",
            id="longer-path",
        ),
        pytest.param(
            ALLOWED.replace("_apis/wit/workitems", "_apis/git/repositories"),
            "not an allowlisted request",
            id="other-endpoint",
        ),
        pytest.param(
            ALLOWED.replace("_apis/wit/workitems", "_apis/wit/wiql"),
            "not an allowlisted request",
            id="wiql-by-get",
        ),
        pytest.param(ALLOWED.replace("api-version=7.1", "api-version=7.2"), "pinned", id="version"),
        pytest.param(
            ALLOWED.replace("api-version=7.1", "api-version=7.1-preview"), "pinned", id="preview"
        ),
        pytest.param(ALLOWED.replace("&api-version=7.1", ""), "pinned", id="no-version"),
        pytest.param(ALLOWED + "&api-version=7.1", "repeated", id="repeated-version"),
        pytest.param(ALLOWED + "&bypassRules=true", "not allowed", id="bypass-rules"),
        pytest.param(ALLOWED + "&$expand=all", "not allowed", id="expand"),
        pytest.param(ALLOWED + "&ids=2", "repeated", id="repeated-ids"),
    ],
)
def test_a_request_outside_the_allowlist_is_rejected(url: str, reason: str) -> None:
    with pytest.raises(RequestNotAllowedError, match=reason):
        _check(url)


@pytest.mark.parametrize("method", ["POST", "PATCH", "DELETE", "PUT", "HEAD", "OPTIONS"])
def test_only_the_allowlisted_method_reaches_an_endpoint(method: str) -> None:
    with pytest.raises(RequestNotAllowedError, match="not an allowlisted request"):
        _check(ALLOWED, method=method)


@pytest.mark.parametrize("header", ["X-HTTP-Method-Override", "x-http-method", "X-Method-Override"])
def test_a_method_override_header_is_rejected(header: str) -> None:
    # Azure DevOps applies the override, so the method checked would not be the method sent.
    with pytest.raises(RequestNotAllowedError, match="method override"):
        _check(ALLOWED, headers={header: "PATCH"})


def test_a_host_header_for_another_host_is_rejected() -> None:
    # The connection goes to dev.azure.com, but a front end could route on the header.
    with pytest.raises(RequestNotAllowedError, match="Host header"):
        _check(ALLOWED, headers={"Host": "evil.test"})


@pytest.mark.parametrize(
    "query",
    [
        pytest.param("ids=1;api-version=9.9&api-version=7.1", id="semicolon-separator"),
        pytest.param("ids=1&api-version=7.1&", id="trailing-separator"),
    ],
)
def test_a_query_that_could_be_read_two_ways_is_rejected(query: str) -> None:
    with pytest.raises(RequestNotAllowedError, match="canonical"):
        _check(f"{CONFIG.base_url}_apis/wit/workitems?{query}")


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("contoso%2FSandbox/_apis/wit/workitems", id="encoded-slash-in-project"),
        pytest.param("contoso/Sandbox/_apis%2Fwit%2Fworkitems", id="encoded-slash-in-path"),
        pytest.param("contoso/Sandbox/_apis/wit%5Cworkitems", id="encoded-backslash"),
    ],
)
def test_an_encoded_separator_is_rejected(path: str) -> None:
    with pytest.raises(RequestNotAllowedError, match=r"encoded separator|outside"):
        _check(f"https://dev.azure.com/{path}?ids=1&api-version=7.1")


WIQL = f"{CONFIG.base_url}_apis/wit/wiql?%24top=5&api-version=7.1"


def test_a_wiql_query_passes() -> None:
    _check(WIQL, method="POST", json={"query": "SELECT [System.Id] FROM WorkItems"})


@pytest.mark.parametrize(
    ("url", "reason"),
    [
        pytest.param(WIQL.replace("wiql?", "wiql/12?"), "not an allowlisted", id="stored-query"),
        pytest.param(WIQL.replace("7.1", "7.2"), "pinned", id="version"),
        pytest.param(WIQL + "&timePrecision=true", "not allowed", id="time-precision"),
        pytest.param(WIQL + "&%24top=6", "repeated", id="repeated-top"),
    ],
)
def test_a_wiql_request_outside_the_allowlist_is_rejected(url: str, reason: str) -> None:
    with pytest.raises(RequestNotAllowedError, match=reason):
        _check(url, method="POST", json={"query": "SELECT [System.Id] FROM WorkItems"})


def test_a_streamed_body_cannot_hide_from_the_body_check() -> None:
    async def body() -> "AsyncIterator[bytes]":
        yield b'{"query": "select *"}'  # pragma: no cover - never sent

    with pytest.raises(RequestNotAllowedError, match="no body"):
        _transport().check(httpx.Request("GET", ALLOWED, content=body()))


def test_a_get_may_not_carry_a_body() -> None:
    with pytest.raises(RequestNotAllowedError, match="no body"):
        _check(ALLOWED, content=b'{"query": "select *"}')


@pytest.mark.anyio
async def test_a_rejected_request_never_reaches_the_inner_transport() -> None:
    sent: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200)

    transport = AllowlistTransport(
        httpx.MockTransport(record), base_path=CONFIG.base_path, allowed=operations("read")
    )
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(RequestNotAllowedError):
            await client.delete(ALLOWED)
        await client.get(ALLOWED)

    assert [request.method for request in sent] == ["GET"]
