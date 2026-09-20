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

import httpx

from azure_devops.config import HOST

__all__ = [
    "ALLOWLIST",
    "AllowedRequest",
    "AllowlistTransport",
    "RequestNotAllowedError",
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


# Pinned api-versions (ADR 0005). Changing one is a safety-critical PR that links the
# API's change notes for the affected endpoints.
ALLOWLIST: Final = (
    AllowedRequest(
        operation="get-work-items",
        kind="read",
        method="GET",
        path="_apis/wit/workitems",
        api_version="7.1",
        query=frozenset({"ids", "fields", "errorPolicy"}),
    ),
)


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
        if url.userinfo or url.fragment:
            raise RequestNotAllowedError("credentials and fragments do not belong in a request URL")
        if not url.path.startswith(self._base_path):
            raise RequestNotAllowedError(f"{url.path} is outside {self._base_path}")

        path = url.path.removeprefix(self._base_path)
        for allowed in self._allowed:
            if allowed.method == request.method and _path_matches(allowed.path, path):
                self._check_query(request, allowed)
                return allowed
        raise RequestNotAllowedError(f"{request.method} {path} is not an allowlisted request")

    def _check_query(self, request: httpx.Request, allowed: AllowedRequest) -> None:
        values: Mapping[str, list[str]] = _grouped(request.url.params.multi_items())
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
        if allowed.method == "GET" and request.content:
            raise RequestNotAllowedError(f"{allowed.operation} takes no body")


def _grouped(items: Iterator[tuple[str, str]] | list[tuple[str, str]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for name, value in items:
        grouped.setdefault(name, []).append(value)
    return grouped
