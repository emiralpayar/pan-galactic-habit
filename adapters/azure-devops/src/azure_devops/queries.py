"""Work item queries, built from structured filters (ADR 0005).

The agent never supplies WIQL. It picks filter values, and this module writes the whole
query around them, always confined to the configured project. A value is restricted to a
character set that cannot end a WIQL string literal or name a field or macro, so there is
nothing to escape: any other value is refused before a request is built.
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, Strict

__all__ = ["WorkItemQuery"]

# Letters, digits, and `_` (\w), plus inner spaces, `-`, and `.`: enough for type, state, and
# tag names, and nothing that WIQL treats as syntax (`'`, `"`, `[`, `]`, `@`, `(`, `)`, `,`).
FilterValue = Annotated[str, Strict(), Field(pattern=r"^\w(?:[\w .-]{0,126}\w)?$", max_length=128)]
FilterValues = Annotated[tuple[FilterValue, ...], Field(max_length=10)]


class WorkItemQuery(BaseModel):
    """Which work items to find. Every filter narrows the result; none can widen it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    types: FilterValues = ()
    states: FilterValues = ()
    tags: FilterValues = ()
    # None means the configured cap, `AzureDevOpsConfig.max_query_results`.
    limit: Annotated[int, Strict(), Field(gt=0)] | None = None

    def to_wiql(self) -> str:
        # The project clause comes first and is not optional: at the project's URL, a
        # query without it still returns work items from every project in the organization.
        clauses = ["[System.TeamProject] = @project"]
        if self.types:
            clauses.append(f"[System.WorkItemType] IN ({_quoted(self.types)})")
        if self.states:
            clauses.append(f"[System.State] IN ({_quoted(self.states)})")
        clauses.extend(f"[System.Tags] CONTAINS '{tag}'" for tag in self.tags)
        # WIQL has no parameters to bind. The values are safe to interpolate only because
        # `FilterValue` cannot contain WIQL syntax; loosening its pattern reopens this.
        where = " AND ".join(clauses)
        return f"SELECT [System.Id] FROM WorkItems WHERE {where} ORDER BY [System.ChangedDate] DESC"  # noqa: S608


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)
