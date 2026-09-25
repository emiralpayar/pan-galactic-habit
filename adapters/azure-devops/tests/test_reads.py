import json
import traceback
from collections.abc import Callable

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from azure_devops.allowlist import RequestNotAllowedError
from azure_devops.config import AzureDevOpsConfig
from azure_devops.queries import WorkItemQuery
from azure_devops.reads import AzureDevOpsError, ReadCapExceededError, WorkItemReader

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


def _reader(
    handler: Callable[[httpx.Request], httpx.Response], config: AzureDevOpsConfig = CONFIG
) -> WorkItemReader:
    return WorkItemReader(config, transport=httpx.MockTransport(handler))


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
# Azure DevOps answers a bad token with 203 and a sign-in page, so only 200 is a success.
@pytest.mark.parametrize("status", [203, 400, 401, 403, 404, 429, 500, 503])
async def test_an_error_response_raises_without_quoting_the_body(status: int) -> None:
    async with _reader(_responds({"message": "Work item 7: secret title"}, status)) as reader:
        with pytest.raises(AzureDevOpsError, match=f"get-work-items returned {status}") as raised:
            await reader.get_work_items([7])

    assert "secret title" not in str(raised.value)


@pytest.mark.anyio
async def test_a_redirect_is_not_followed() -> None:
    elsewhere = "https://evil.test/contoso/Sandbox/_apis/wit/workitems?ids=1&api-version=7.1"
    seen: list[httpx.URL] = []

    def redirect(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        return httpx.Response(302, headers={"location": elsewhere})

    async with _reader(redirect) as reader:
        with pytest.raises(AzureDevOpsError, match="returned 302"):
            await reader.get_work_items([1])

    # The credential travels with the request, so it must not follow a redirect anywhere.
    assert [url.host for url in seen] == ["dev.azure.com"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"count": 1}, id="no-value"),
        pytest.param({"count": 1, "value": [{"id": 1}]}, id="no-fields"),
        pytest.param(
            {
                "count": 1,
                "value": [
                    {
                        "id": 1,
                        "rev": 1,
                        "project": "Sandbox",
                        "type": "Bug",
                        "title": "t",
                        "state": "New",
                    }
                ],
            },
            id="flat-item-without-fields",
        ),
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
@pytest.mark.parametrize(
    "response",
    [
        pytest.param(httpx.Response(200, text="<html>Sign in SECRET-BODY</html>"), id="not-json"),
        pytest.param(
            httpx.Response(
                200, json={"count": 1, "value": [{**_work_item(1), "rev": "SECRET-BODY"}]}
            ),
            id="wrong-type",
        ),
    ],
)
async def test_an_unexpected_payload_is_not_quoted(response: httpx.Response) -> None:
    # The payload is untrusted content; an error that quoted it could carry injected text
    # into a log or an agent's context (ARCHITECTURE.md §5.3).
    async with _reader(lambda _: response) as reader:
        with pytest.raises(AzureDevOpsError, match="unexpected") as raised:
            await reader.get_work_items([1])

    assert "SECRET-BODY" not in "".join(traceback.format_exception(raised.value))


@pytest.mark.anyio
async def test_an_unexpected_payload_names_where_it_failed() -> None:
    items = [{"id": id_, "rev": 1, "fields": {}} for id_ in range(1, 6)]
    async with _reader(_responds({"count": 5, "value": items})) as reader:
        with pytest.raises(AzureDevOpsError) as raised:
            await reader.get_work_items([1])

    # Each item lacks four required fields; only the first three problems are listed.
    assert str(raised.value) == (
        "unexpected WorkItemBatch payload: string_type at value.0.project, "
        "string_type at value.0.type, string_type at value.0.title, and 17 more"
    )


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


SMALL_SESSION = CONFIG.model_copy(update={"max_work_items_per_session": 3})


@pytest.mark.anyio
async def test_a_read_past_the_session_cap_is_refused_before_it_is_sent() -> None:
    sent: list[str] = []

    def record(request: httpx.Request) -> httpx.Response:
        sent.append(request.url.params["ids"])
        return httpx.Response(200, json={"count": 0, "value": []})

    async with _reader(record, SMALL_SESSION) as reader:
        await reader.get_work_items([1, 2])
        with pytest.raises(ReadCapExceededError, match="session cap of 3"):
            await reader.get_work_items([3, 4])
        await reader.get_work_items([3])
        with pytest.raises(ReadCapExceededError):
            await reader.get_work_items([1])

    assert sent == ["1,2", "3"]


@pytest.mark.anyio
async def test_ids_count_toward_the_session_cap_even_when_the_read_fails() -> None:
    async with _reader(_responds({}, status=500), SMALL_SESSION) as reader:
        with pytest.raises(AzureDevOpsError):
            await reader.get_work_items([1, 2, 3])
        with pytest.raises(ReadCapExceededError):
            await reader.get_work_items([4])


@pytest.mark.anyio
async def test_ids_count_toward_the_session_cap_even_when_nothing_comes_back() -> None:
    async with _reader(_responds({"count": 0, "value": []}), SMALL_SESSION) as reader:
        assert await reader.get_work_items([1, 2, 3]) == ()
        with pytest.raises(ReadCapExceededError):
            await reader.get_work_items([4])


@pytest.mark.anyio
async def test_duplicate_ids_count_once_toward_the_session_cap() -> None:
    async with _reader(_responds({"count": 0, "value": []}), SMALL_SESSION) as reader:
        await reader.get_work_items([1, 1, 2, 2, 3])
        with pytest.raises(ReadCapExceededError, match="0 remain"):
            await reader.get_work_items([4])


@pytest.mark.parametrize("cap", [0, -1, 1001])
def test_the_session_cap_must_be_bounded(cap: int) -> None:
    with pytest.raises(ValidationError, match="max_work_items_per_session"):
        CONFIG.model_validate({**CONFIG.model_dump(), "max_work_items_per_session": cap})


def _query_result(*ids: int) -> dict[str, object]:
    return {
        "queryType": "flat",
        "workItems": [
            {"id": id_, "url": f"https://dev.azure.com/contoso/_apis/wit/workItems/{id_}"}
            for id_ in ids
        ],
    }


def _recorded_queries(
    sent: list[httpx.Request], payload: object
) -> Callable[[httpx.Request], httpx.Response]:
    def record(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json=payload)

    return record


@pytest.mark.anyio
async def test_finds_work_items_with_a_project_confined_query() -> None:
    sent: list[httpx.Request] = []
    query = WorkItemQuery(types=("User Story", "Bug"), states=("New",), tags=("needs-refinement",))
    async with _reader(_recorded_queries(sent, _query_result(4, 2))) as reader:
        assert await reader.find_work_items(query) == (4, 2)

    request = sent[0]
    assert request.method == "POST"
    assert request.url.path == "/contoso/Sandbox/_apis/wit/wiql"
    assert dict(request.url.params) == {"$top": "50", "api-version": "7.1"}
    assert json.loads(request.content) == {
        "query": (
            "SELECT [System.Id] FROM WorkItems"
            " WHERE [System.TeamProject] = @project"
            " AND [System.WorkItemType] IN ('User Story', 'Bug')"
            " AND [System.State] IN ('New')"
            " AND [System.Tags] CONTAINS 'needs-refinement'"
            " ORDER BY [System.ChangedDate] DESC"
        )
    }


@pytest.mark.anyio
async def test_an_empty_query_is_still_confined_to_the_project() -> None:
    sent: list[httpx.Request] = []
    async with _reader(_recorded_queries(sent, _query_result())) as reader:
        assert await reader.find_work_items(WorkItemQuery()) == ()

    assert json.loads(sent[0].content)["query"] == (
        "SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project"
        " ORDER BY [System.ChangedDate] DESC"
    )


@pytest.mark.anyio
async def test_a_smaller_limit_is_sent_as_top() -> None:
    sent: list[httpx.Request] = []
    async with _reader(_recorded_queries(sent, _query_result())) as reader:
        await reader.find_work_items(WorkItemQuery(limit=5))

    assert sent[0].url.params["$top"] == "5"


@pytest.mark.anyio
async def test_results_past_the_limit_are_dropped_even_if_azure_devops_sends_them() -> None:
    async with _reader(_responds(_query_result(*range(1, 20)))) as reader:
        assert await reader.find_work_items(WorkItemQuery(limit=3)) == (1, 2, 3)


@pytest.mark.anyio
async def test_a_limit_over_the_configured_cap_is_refused_before_a_request_is_sent() -> None:
    def unreachable(_: httpx.Request) -> httpx.Response:  # pragma: no cover - must not run
        raise AssertionError("a request was sent")

    async with _reader(unreachable) as reader:
        with pytest.raises(ValueError, match="exceeds the cap of 50"):
            await reader.find_work_items(WorkItemQuery(limit=51))


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("Bug') OR [System.TeamProject] <> @project OR ('", id="quote"),
        pytest.param('Bug"', id="double-quote"),
        pytest.param("[System.Id]", id="brackets"),
        pytest.param("@project", id="macro"),
        pytest.param("Bug\nNew", id="newline"),
        pytest.param("", id="empty"),
        pytest.param(" Bug", id="leading-space"),
        pytest.param("x" * 129, id="too-long"),
    ],
)
@pytest.mark.parametrize("field", ["types", "states", "tags"])
def test_a_value_that_could_change_the_query_is_refused(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        WorkItemQuery.model_validate({field: [value]})


@pytest.mark.parametrize("extra", [{"wiql": "SELECT *"}, {"project": "Other"}, {"limit": 0}])
def test_a_query_takes_only_structured_filters(extra: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        WorkItemQuery.model_validate(extra)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"workItems": [{"id": 0}]}, id="zero-id"),
        pytest.param({"workItems": [{"id": "1"}]}, id="string-id"),
        pytest.param({"queryType": "flat"}, id="no-work-items"),
    ],
)
async def test_an_unexpected_query_result_raises(payload: object) -> None:
    async with _reader(_responds(payload)) as reader:
        with pytest.raises(AzureDevOpsError, match="unexpected QueryResult payload"):
            await reader.find_work_items(WorkItemQuery())


@pytest.mark.anyio
async def test_a_failed_query_raises_without_quoting_the_body() -> None:
    async with _reader(_responds({"message": "secret content"}, status=400)) as reader:
        with pytest.raises(AzureDevOpsError, match="find-work-items returned 400") as raised:
            await reader.find_work_items(WorkItemQuery())

    assert "secret content" not in str(raised.value)
