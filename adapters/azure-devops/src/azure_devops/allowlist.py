"""The request allowlist, enforced as the last step before a request leaves the process.

ADR 0005 allowlists requests, not just operations: an operation is reachable only as one
exact method, path, set of query parameters, and pinned `api-version`. Putting the check in
an httpx transport makes it independent of the code that builds the request, so a mistake
in an operation, or a future caller that builds its own request, still cannot reach an
endpoint that is not listed here.
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Final, Literal
from urllib.parse import quote, urlencode

import httpx

from azure_devops.config import HOST

__all__ = [
    "ALLOWLIST",
    "AllowedRequest",
    "AllowlistTransport",
    "RequestNotAllowedError",
    "find",
    "operations",
]


class RequestNotAllowedError(Exception):
    """The request is not on the allowlist and was not sent."""


@dataclass(frozen=True, slots=True)
class AllowedRequest:
    """One request the adapter may send.

    `path` is relative to the organization and project, and may contain `{id}`, which
    matches one or more digits. `query` lists the query parameter names the request may
    carry besides `api-version`; each may appear only once.
    """

    operation: str
    kind: Literal["read", "write"]
    method: Literal["GET", "POST", "PATCH"]
    path: str
    api_version: str
    query: frozenset[str] = field(default_factory=frozenset)


# Azure DevOps applies these instead of the method on the wire, so a POST that passed the
# check as a read could arrive as a PATCH.
_METHOD_OVERRIDE_HEADERS: Final = frozenset(
    {"x-http-method-override", "x-http-method", "x-method-override"}
)

# Pinned api-versions (ADR 0005). Changing one is a safety-critical PR that links the
# API's change notes for the affected endpoints.
ALLOWLIST: Final = (
    AllowedRequest(
        operation="get-work-items",
        kind="read",
        method="GET",
        path="_apis/wit/workitems",
        api_version="7.1",
        # `ids` is organization-scoped: this entry does not confine the request to the
        # configured project, so the caller drops work items from other projects.
        query=frozenset({"ids", "fields", "errorPolicy"}),
    ),
)


def find(operation: str) -> AllowedRequest:
    """The allowlist entry for one operation, so its path and api-version have one source."""
    for request in ALLOWLIST:
        if request.operation == operation:
            return request
    raise KeyError(operation)


def operations(kind: Literal["read", "write"]) -> tuple[AllowedRequest, ...]:
    """The allowlisted requests of one kind, for a client that may send only those."""
    return tuple(request for request in ALLOWLIST if request.kind == kind)


def _path_matches(template: str, path: str) -> bool:
    expected = template.split("/")
    actual = path.split("/")
    if len(expected) != len(actual):
        return False
    return all(
        (actual_segment.isascii() and actual_segment.isdigit())
        if expected_segment == "{id}"
        else expected_segment == actual_segment
        for expected_segment, actual_segment in zip(expected, actual, strict=True)
    )


class AllowlistTransport(httpx.AsyncBaseTransport):
    """Rejects any request that is not exactly one of `allowed` before it is sent."""

    def __init__(
        self,
        inner: httpx.AsyncBaseTransport,
        *,
        base_path: str,
        allowed: tuple[AllowedRequest, ...],
    ) -> None:
        self._inner = inner
        self._base_path = base_path
        self._allowed = allowed

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.check(request)
        return await self._inner.handle_async_request(request)

    async def aclose(self) -> None:
        await self._inner.aclose()

    def check(self, request: httpx.Request) -> AllowedRequest:
        """Return the allowlist entry this request matches, or raise `RequestNotAllowedError`."""
        url = request.url
        if url.scheme != "https" or url.host != HOST or url.port not in (None, 443):
            raise RequestNotAllowedError(f"{url.scheme}://{url.netloc.decode()} is not {HOST}")
        # The connection goes to the URL's host, but a front end could route on the header.
        if request.headers.get("host") != HOST:
            raise RequestNotAllowedError(f"the Host header is not {HOST}")
        if url.userinfo or url.fragment:
            raise RequestNotAllowedError("credentials and fragments do not belong in a request URL")
        if not url.path.startswith(self._base_path):
            raise RequestNotAllowedError(f"{url.path} is outside {self._base_path}")

        if overrides := sorted(
            _METHOD_OVERRIDE_HEADERS & {name.lower() for name in request.headers}
        ):
            raise RequestNotAllowedError(f"method override headers: {overrides}")
        raw_path = url.raw_path.split(b"?")[0].decode()
        if "%2f" in raw_path.casefold() or "%5c" in raw_path.casefold():
            raise RequestNotAllowedError("an encoded separator makes the path ambiguous")

        path = url.path.removeprefix(self._base_path)
        for allowed in self._allowed:
            if allowed.method == request.method and _path_matches(allowed.path, path):
                self._check_query(request, allowed)
                return allowed
        raise RequestNotAllowedError(f"{request.method} {path} is not an allowlisted request")

    def _check_query(self, request: httpx.Request, allowed: AllowedRequest) -> None:
        items = list(request.url.params.multi_items())
        values: Mapping[str, list[str]] = _grouped(items)
        if repeated := sorted(name for name, seen in values.items() if len(seen) > 1):
            raise RequestNotAllowedError(f"repeated query parameters: {repeated}")
        if unlisted := sorted(set(values) - allowed.query - {"api-version"}):
            raise RequestNotAllowedError(
                f"query parameters not allowed for {allowed.operation}: {unlisted}"
            )
        if values.get("api-version") != [allowed.api_version]:
            raise RequestNotAllowedError(
                f"{allowed.operation} is pinned to api-version {allowed.api_version}"
            )
        # `?ids=1;api-version=9.9` parses as one parameter above, but anything in front of
        # Azure DevOps that still splits on `;` would read a different api-version than the
        # one checked here. Requiring the raw query to match its own re-encoding removes
        # every such difference between what is checked and what is sent.
        if request.url.query.decode() != urlencode(items, quote_via=quote, safe=""):
            raise RequestNotAllowedError("the query string is not in canonical form")
        if allowed.method == "GET" and self._has_body(request):
            raise RequestNotAllowedError(f"{allowed.operation} takes no body")

    @staticmethod
    def _has_body(request: httpx.Request) -> bool:
        try:
            return bool(request.content)
        except httpx.StreamError:
            # A streamed body cannot be inspected, so it cannot be shown to be empty.
            return True


def _grouped(items: Iterator[tuple[str, str]] | list[tuple[str, str]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for name, value in items:
        grouped.setdefault(name, []).append(value)
    return grouped
