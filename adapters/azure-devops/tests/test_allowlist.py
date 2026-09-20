import httpx
import pytest
from azure_devops.allowlist import ALLOWLIST, AllowlistTransport, RequestNotAllowedError, operations
from azure_devops.config import AzureDevOpsConfig
from pydantic import SecretStr

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
            id="not-implemented-yet",
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
