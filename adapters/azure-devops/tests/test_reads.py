import json
from collections.abc import Callable

import httpx
import pytest
from azure_devops.allowlist import RequestNotAllowedError
from azure_devops.config import AzureDevOpsConfig
from azure_devops.reads import AzureDevOpsError, WorkItemReader
from pydantic import SecretStr

CONFIG = AzureDevOpsConfig(
    organization="contoso", project="Sandbox", token=SecretStr("not-a-real-token")
)


def _work_item(id_: int = 1, project: str = "Sandbox", **fields: str) -> dict[str, object]:
    return {
        "id": id_,
        "rev": 3,
        "url": f"https://dev.azure.com/contoso/_apis/wit/workItems/{id_}",
        "fields": {
            "System.TeamProject": project,
            "System.WorkItemType": "User Story",
            "System.Title": "Refine me",
            "System.State": "New",
            **fields,
        },
    }


def _reader(handler: Callable[[httpx.Request], httpx.Response]) -> WorkItemReader:
    return WorkItemReader(CONFIG, transport=httpx.MockTransport(handler))


def _responds(payload: object, status: int = 200) -> Callable[[httpx.Request], httpx.Response]:
    return lambda _: httpx.Response(status, json=payload)


@pytest.mark.anyio
async def test_reads_a_work_item() -> None:
    payload = _work_item(
        7,
        **{
            "System.Description": "<div>needs work</div>",
            "Microsoft.VSTS.Common.AcceptanceCriteria": "<ul><li>one</li></ul>",
            "System.Tags": "backlog; needs-refinement ;",
        },
    )
    async with _reader(_responds({"count": 1, "value": [payload]})) as reader:
        items = await reader.get_work_items([7])

    assert len(items) == 1
    item = items[0]
    assert (item.id, item.rev, item.title, item.state) == (7, 3, "Refine me", "New")
    assert item.description == "<div>needs work</div>"
    assert item.acceptance_criteria == "<ul><li>one</li></ul>"
    assert item.tags == ("backlog", "needs-refinement")


@pytest.mark.anyio
async def test_the_request_is_confined_to_the_configured_project() -> None:
    seen: list[httpx.URL] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        return httpx.Response(200, json={"count": 0, "value": []})

    async with _reader(record) as reader:
        await reader.get_work_items([1, 2])

    url = seen[0]
    assert url.path == "/contoso/Sandbox/_apis/wit/workitems"
    assert dict(url.params) == {
        "ids": "1,2",
        "fields": (
            "System.TeamProject,System.WorkItemType,System.Title,System.State,"
            "System.Description,Microsoft.VSTS.Common.AcceptanceCriteria,System.Tags"
        ),
        "errorPolicy": "omit",
        "api-version": "7.1",
    }


@pytest.mark.anyio
async def test_the_token_travels_only_as_basic_auth() -> None:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"count": 0, "value": []})

    async with _reader(record) as reader:
        await reader.get_work_items([1])

    request = seen[0]
    assert request.headers["authorization"].startswith("Basic ")
    assert "not-a-real-token" not in str(request.url)
    assert "not-a-real-token" not in repr(CONFIG)


@pytest.mark.anyio
async def test_work_items_from_another_project_are_dropped() -> None:
    payload = {
        "count": 3,
        "value": [
            _work_item(1, project="Other"),
            _work_item(2, project="sandbox"),  # Azure DevOps project names are case-insensitive.
            _work_item(3),
        ],
    }
    async with _reader(_responds(payload)) as reader:
        items = await reader.get_work_items([1, 2, 3])

    assert [item.id for item in items] == [2, 3]


@pytest.mark.anyio
async def test_ids_azure_devops_omits_are_skipped() -> None:
    payload = {"count": 2, "value": [None, _work_item(2)]}
    async with _reader(_responds(payload)) as reader:
        items = await reader.get_work_items([1, 2])

    assert [item.id for item in items] == [2]


@pytest.mark.anyio
@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500, 503])
async def test_an_error_response_raises_without_quoting_the_body(status: int) -> None:
    async with _reader(_responds({"message": "Work item 7: secret title"}, status)) as reader:
        with pytest.raises(AzureDevOpsError, match=f"returned {status}") as raised:
            await reader.get_work_items([7])

    assert "secret title" not in str(raised.value)


@pytest.mark.anyio
async def test_a_redirect_is_not_followed() -> None:
    elsewhere = "https://evil.test/contoso/Sandbox/_apis/wit/workitems"
    async with _reader(_responds(None, 302)) as reader:
        with pytest.raises(AzureDevOpsError, match="returned 302"):
            await reader.get_work_items([1])
    assert elsewhere  # the redirect target is never requested; see the allowlist tests


@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"count": 1}, id="no-value"),
        pytest.param({"count": 1, "value": [{"id": 1}]}, id="no-fields"),
        pytest.param({"count": 1, "value": [{"id": 1, "rev": 1, "fields": []}]}, id="fields-list"),
        pytest.param(
            {"count": 1, "value": [{"id": 0, "rev": 1, "fields": {}}]}, id="missing-field"
        ),
        pytest.param("not a mapping", id="not-a-mapping"),
    ],
)
async def test_an_unexpected_payload_raises(payload: object) -> None:
    async with _reader(_responds(payload)) as reader:
        with pytest.raises(AzureDevOpsError, match="unexpected"):
            await reader.get_work_items([1])


@pytest.mark.anyio
async def test_a_payload_that_is_not_json_raises() -> None:
    async with _reader(lambda _: httpx.Response(200, text="<html>sign in</html>")) as reader:
        with pytest.raises(AzureDevOpsError, match="unexpected"):
            await reader.get_work_items([1])


@pytest.mark.anyio
async def test_a_transport_failure_raises_without_the_credential() -> None:
    def fail(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    async with _reader(fail) as reader:
        with pytest.raises(AzureDevOpsError, match="failed") as raised:
            await reader.get_work_items([1])

    assert "not-a-real-token" not in str(raised.value)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("ids", "reason"),
    [
        pytest.param([], "no work item ids", id="empty"),
        pytest.param([0], "positive integers", id="zero"),
        pytest.param([-1], "positive integers", id="negative"),
        pytest.param([True], "positive integers", id="bool"),
        pytest.param(["1"], "positive integers", id="string"),
        pytest.param(list(range(1, 60)), "exceeds the cap", id="over-cap"),
    ],
)
async def test_bad_ids_are_refused_before_a_request_is_sent(ids: list[object], reason: str) -> None:
    def unreachable(_: httpx.Request) -> httpx.Response:  # pragma: no cover - must not run
        raise AssertionError("a request was sent")

    async with _reader(unreachable) as reader:
        with pytest.raises(ValueError, match=reason):
            await reader.get_work_items(ids)  # type: ignore[arg-type]


@pytest.mark.anyio
async def test_duplicate_ids_are_sent_once() -> None:
    seen: list[httpx.URL] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        return httpx.Response(200, json={"count": 0, "value": []})

    async with _reader(record) as reader:
        await reader.get_work_items([1, 1, 2])

    assert seen[0].params["ids"] == "1,2"


@pytest.mark.anyio
async def test_a_project_name_from_a_response_cannot_redirect_a_later_read() -> None:
    # Injected content might name another project; the adapter reads only its own.
    payload = json.loads(json.dumps({"count": 1, "value": [_work_item(1, project="Other")]}))
    async with _reader(_responds(payload)) as reader:
        assert await reader.get_work_items([1]) == ()


@pytest.mark.anyio
async def test_the_reader_cannot_send_a_write() -> None:
    async with _reader(_responds({"count": 0, "value": []})) as reader:
        with pytest.raises(RequestNotAllowedError, match="not an allowlisted request"):
            await reader._client.patch(
                "_apis/wit/workitems/1", json=[], params={"api-version": "7.1"}
            )
