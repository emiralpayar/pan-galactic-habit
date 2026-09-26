"""Where the adapter may talk to, and with which credential.

The organization and project are fixed here rather than passed per call, so no content
read from Azure DevOps can steer a later read to another project (ARCHITECTURE.md §5.3).
"""

from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

__all__ = ["HOST", "AzureDevOpsConfig"]

HOST = "dev.azure.com"

# Azure DevOps rejects these in project names; listing them keeps a project name from
# adding a path segment or a query string to every request the adapter builds.
_FORBIDDEN_IN_PROJECT = set('/\\:*?"<>|;#$*{},+=[]%') | {chr(code) for code in range(0x20)}

Organization = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9-]{0,63}$")]


class AzureDevOpsConfig(BaseModel):
    """The one organization and project this adapter reads, and its credential."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    organization: Organization
    project: Annotated[str, Field(min_length=1, max_length=64)]
    token: SecretStr
    # Azure DevOps caps a work item batch at 200; the adapter caps it lower by default.
    max_work_item_ids_per_call: Annotated[int, Field(gt=0, le=200)] = 50
    # ADR 0005 caps read volume per session too. A placeholder, like the policy budgets,
    # until the Backlog Refiner's real usage shows what a session needs. The upper bound
    # keeps a mistyped value from switching the cap off.
    max_work_items_per_session: Annotated[int, Field(gt=0, le=1000)] = 200
    # ADR 0005 caps query results. A placeholder too; Azure DevOps itself allows 20000.
    max_query_results: Annotated[int, Field(gt=0, le=200)] = 50

    @model_validator(mode="after")
    def _project_is_a_single_path_segment(self) -> Self:
        if forbidden := _FORBIDDEN_IN_PROJECT & set(self.project):
            raise ValueError(f"project contains {sorted(forbidden)}")
        if self.project != self.project.strip() or self.project.strip(".") == "":
            raise ValueError("project may not be padded with spaces or consist of dots")
        return self

    @property
    def base_url(self) -> str:
        """Every request the adapter sends starts here."""
        return f"https://{HOST}/{self.organization}/{self.project}/"

    @property
    def base_path(self) -> str:
        """The decoded URL path of `base_url`, which the allowlist transport enforces."""
        return f"/{self.organization}/{self.project}/"
