"""Typed views of the Azure DevOps responses the adapter reads.

Everything here is **untrusted data**: people outside this system write it, and it may
contain prompt injection (ARCHITECTURE.md §5.3). The models make the shape predictable;
they say nothing about the content being safe to act on.
"""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["QueryResult", "WorkItem", "WorkItemBatch"]

PROJECT_FIELD = "System.TeamProject"

# The only fields the adapter asks for. Everything else in a work item stays unread.
WORK_ITEM_FIELDS = (
    PROJECT_FIELD,
    "System.WorkItemType",
    "System.Title",
    "System.State",
    "System.Description",
    "Microsoft.VSTS.Common.AcceptanceCriteria",
    "System.Tags",
)


class _External(BaseModel):
    # Azure DevOps adds keys (`url`, `_links`, …) and may add more in a later api-version,
    # so unknown keys are ignored rather than rejected.
    model_config = ConfigDict(extra="ignore", frozen=True)


class WorkItem(_External):
    id: Annotated[int, Field(gt=0)]
    rev: Annotated[int, Field(gt=0)]
    project: str
    type: str
    title: str
    state: str
    description: str | None = None
    acceptance_criteria: str | None = None
    tags: tuple[str, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def _flatten_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # Every work item Azure DevOps returns carries `fields`. Without it, the values below
        # would come from top-level keys instead, including the project the filter checks.
        fields = data.get("fields")
        if not isinstance(fields, dict):
            raise ValueError("fields must be a mapping")
        tags = fields.get("System.Tags")
        return {
            "id": data.get("id"),
            "rev": data.get("rev"),
            "project": fields.get(PROJECT_FIELD),
            "type": fields.get("System.WorkItemType"),
            "title": fields.get("System.Title"),
            "state": fields.get("System.State"),
            "description": fields.get("System.Description"),
            "acceptance_criteria": fields.get("Microsoft.VSTS.Common.AcceptanceCriteria"),
            "tags": _split_tags(tags) if isinstance(tags, str) else (),
        }


def _split_tags(tags: str) -> tuple[str, ...]:
    return tuple(tag.strip() for tag in tags.split(";") if tag.strip())


class WorkItemBatch(_External):
    """A `workitems` response. With `errorPolicy=omit`, missing ids come back as null."""

    value: tuple[WorkItem | None, ...]

    @property
    def items(self) -> tuple[WorkItem, ...]:
        return tuple(item for item in self.value if item is not None)


class WorkItemReference(_External):
    id: Annotated[int, Field(gt=0, strict=True)]


class QueryResult(_External):
    """A `wiql` response: the ids that matched, in the query's order, and nothing else."""

    work_items: tuple[WorkItemReference, ...] = Field(alias="workItems")

    @property
    def ids(self) -> tuple[int, ...]:
        return tuple(dict.fromkeys(item.id for item in self.work_items))
