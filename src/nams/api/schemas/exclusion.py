"""Pydantic schemas for Exclusion Rules."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

RuleType = Literal["size", "duration", "keyword"]
Operator = Literal["lt", "gt", "eq", "contains"]


class ExclusionRuleBase(BaseModel):
    """Base exclusion rule schema."""
    rule_type: RuleType
    operator: Operator
    value: str
    description: str | None = None
    is_active: bool = True

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str, info) -> str:
        """Validate value based on rule_type."""
        rule_type = info.data.get("rule_type")
        if rule_type in ("size", "duration"):
            try:
                int(v)
            except ValueError:
                raise ValueError(f"Value must be numeric for {rule_type} rules")
        return v


class ExclusionRuleCreate(ExclusionRuleBase):
    """Exclusion rule creation schema."""
    pass


class ExclusionRuleUpdate(BaseModel):
    """Exclusion rule update schema."""
    rule_type: RuleType | None = None
    operator: Operator | None = None
    value: str | None = None
    description: str | None = None
    is_active: bool | None = None


class ExclusionRuleResponse(ExclusionRuleBase):
    """Exclusion rule response schema."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExclusionRuleListResponse(BaseModel):
    """Exclusion rule list response."""
    items: list[ExclusionRuleResponse]
    total: int


class ExclusionRuleTestRequest(BaseModel):
    """Test exclusion rule against sample data."""
    rule_type: RuleType
    operator: Operator
    value: str
    sample_filename: str | None = None
    sample_size_bytes: int | None = None
    sample_duration_sec: int | None = None


class ExclusionRuleTestResult(BaseModel):
    """Result of exclusion rule test."""
    would_exclude: bool
    reason: str
