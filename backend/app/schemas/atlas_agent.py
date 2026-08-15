from typing import Literal

from pydantic import BaseModel, Field, field_validator


Priority = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class RequirementOutput(BaseModel):
    title: str = Field(min_length=3)
    description: str = Field(min_length=5)
    category: str = Field(min_length=2)
    priority: Priority = "MEDIUM"
    section: str | None = None
    source_text: str = Field(min_length=5)
    confidence: float = Field(ge=0, le=1)


class RequirementExtraction(BaseModel):
    requirements: list[RequirementOutput] = Field(min_length=1)


class ProposalOutput(BaseModel):
    title: str = Field(min_length=3)
    description: str = Field(min_length=5)
    requirement_ids: list[str] = Field(min_length=1)
    priority: Priority = "MEDIUM"
    dependencies: list[str] = []
    acceptance_criteria: list[str] = Field(min_length=1)
    suggested_assignee_id: int | None = None
    confidence: float = Field(ge=0, le=1)

    @field_validator("requirement_ids", "acceptance_criteria")
    @classmethod
    def no_blank_values(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("blank list entries are not allowed")
        return values


class ProposalPlan(BaseModel):
    tasks: list[ProposalOutput] = Field(min_length=1)


class ProposalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3)
    description: str | None = Field(default=None, min_length=5)
    priority: Priority | None = None
    dependencies: list[str] | None = None
    acceptance_criteria: list[str] | None = Field(default=None, min_length=1)
    suggested_assignee_id: int | None = None


class GenerateProposalRequest(BaseModel):
    requirement_ids: list[str] = Field(min_length=1)


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)


class ProjectMemberCreate(BaseModel):
    user_id: int
    project_role: Literal["MANAGER", "TEAM_LEAD", "SENIOR_DEVELOPER", "JUNIOR_DEVELOPER", "INTERN"]
    skills: list[str] = []
    experience_level: str = "STANDARD"
    current_capacity: float = Field(default=1.0, gt=0, le=2)


class AssignmentApproveRequest(BaseModel):
    member_id: int | None = None
