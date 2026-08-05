"""Time primitives that preserve explicit UTC instants and coverage."""

from dataclasses import dataclass
from datetime import UTC, datetime


def as_utc(value: datetime, field_name: str = "timestamp") -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class TimeRange:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        start = as_utc(self.start, "range start")
        end = as_utc(self.end, "range end")
        if end < start:
            raise ValueError("range end cannot precede range start")
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)
