"""Read operations. Reads are ungated but untrusted (ARCHITECTURE.md §3).

Results carry no authority: the caller treats every value as data written by someone
outside this system. Writes are not reachable from here; they go through the Safety Layer.
"""

import types
from collections.abc import Sequence
from typing import Self

import httpx
from pydantic import ValidationError

from azure_devops.allowlist import AllowedRequest, AllowlistTransport, find, operations
from azure_devops.config import AzureDevOpsConfig
from azure_devops.models import WORK_ITEM_FIELDS, WorkItem, WorkItemBatch

__all__ = ["AzureDevOpsError", "WorkItemReader"]

# The path and api-version come from the allowlist, so a version bump has one place to change.
GET_WORK_ITEMS = find("get-work-items")
TIMEOUT_SECONDS = 30.0


class AzureDevOpsError(Exception):
    """Azure DevOps refused the request or answered with something unusable."""


class WorkItemReader:
    """Reads work items from the one project in `config`."""

    def __init__(
        self, config: AzureDevOpsConfig, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            # Azure DevOps takes a personal access token as the basic-auth password.
            auth=httpx.BasicAuth("", config.token.get_secret_value()),
            transport=AllowlistTransport(
                transport or httpx.AsyncHTTPTransport(),
                base_path=config.base_path,
                allowed=operations("read"),
            ),
            timeout=TIMEOUT_SECONDS,
            # A redirect could send the request, and its credential, somewhere unlisted.
            follow_redirects=False,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_work_items(self, ids: Sequence[int]) -> tuple[WorkItem, ...]:
        """Read work items by id, dropping any that belong to another project.

        Ids Azure DevOps cannot return are omitted rather than failing the whole batch.
        """
        requested = self._checked_ids(ids)
        response = await self._get(
            GET_WORK_ITEMS,
            {
                "ids": ",".join(str(id_) for id_ in requested),
                "fields": ",".join(WORK_ITEM_FIELDS),
                "errorPolicy": "omit",
                "api-version": GET_WORK_ITEMS.api_version,
            },
        )
        batch = self._parse(response, WorkItemBatch)
        project = self._config.project.casefold()
        return tuple(item for item in batch.items if item.project.casefold() == project)

    def _checked_ids(self, ids: Sequence[int]) -> tuple[int, ...]:
        if not ids:
            raise ValueError("no work item ids given")
        if any(isinstance(id_, bool) or not isinstance(id_, int) or id_ <= 0 for id_ in ids):
            raise ValueError("work item ids must be positive integers")
        unique = tuple(dict.fromkeys(ids))
        if len(unique) > self._config.max_work_item_ids_per_call:
            raise ValueError(
                f"{len(unique)} ids exceeds the cap of {self._config.max_work_item_ids_per_call}"
            )
        return unique

    async def _get(self, operation: AllowedRequest, params: dict[str, str]) -> httpx.Response:
        try:
            response = await self._client.get(operation.path, params=params)
        except httpx.HTTPError as error:
            # str(error) can hold the request URL but never the Authorization header.
            raise AzureDevOpsError(f"{operation.operation} failed: {error}") from error
        if response.is_success:
            return response
        # The body can quote work item content, so only the status line is reported.
        raise AzureDevOpsError(f"{operation.operation} returned {response.status_code}")

    def _parse[T: WorkItemBatch](self, response: httpx.Response, model: type[T]) -> T:
        try:
            return model.model_validate_json(response.content)
        except ValidationError as error:
            raise AzureDevOpsError(f"unexpected {model.__name__} payload: {error}") from error
