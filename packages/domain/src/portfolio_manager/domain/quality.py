"""Structured source-quality and freshness primitives."""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from portfolio_manager.domain.temporal import TimeRange, as_utc


class Authority(StrEnum):
    AUTHORITATIVE = "authoritative"
    RECONSTRUCTED = "reconstructed"
    ESTIMATED = "estimated"


class Completeness(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class SettlementState(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    PENDING = "pending"
    SETTLED = "settled"
    UNKNOWN = "unknown"


_ISSUE_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")


@dataclass(frozen=True, slots=True, order=True)
class QualityIssue:
    code: str

    def __post_init__(self) -> None:
        if _ISSUE_CODE.fullmatch(self.code) is None:
            raise ValueError("quality issue code must be a stable lowercase identifier")


@dataclass(frozen=True, slots=True)
class DataQuality:
    authority: Authority
    completeness: Completeness
    observed_at: datetime
    data_through: datetime | None = None
    coverage: TimeRange | None = None
    settlement: SettlementState = SettlementState.NOT_APPLICABLE
    issues: tuple[QualityIssue, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_at", as_utc(self.observed_at, "observed_at"))
        if self.data_through is not None:
            object.__setattr__(
                self,
                "data_through",
                as_utc(self.data_through, "data_through"),
            )
        if len(set(self.issues)) != len(self.issues):
            raise ValueError("quality issue codes must not be duplicated")
