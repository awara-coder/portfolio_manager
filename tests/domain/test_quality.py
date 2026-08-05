from datetime import UTC, datetime, timedelta, timezone

import pytest

from portfolio_manager.domain import (
    Authority,
    Completeness,
    DataQuality,
    QualityIssue,
    SettlementState,
    TimeRange,
    as_utc,
)


def test_time_range_normalizes_instants_to_utc() -> None:
    ist = timezone(timedelta(hours=5, minutes=30))
    coverage = TimeRange(
        datetime(2026, 8, 5, 9, tzinfo=ist),
        datetime(2026, 8, 5, 17, tzinfo=ist),
    )

    assert coverage.start == datetime(2026, 8, 5, 3, 30, tzinfo=UTC)
    assert coverage.end == datetime(2026, 8, 5, 11, 30, tzinfo=UTC)


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        as_utc(datetime(2026, 8, 5))


def test_invalid_time_range_is_rejected() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValueError, match="cannot precede"):
        TimeRange(now, now - timedelta(seconds=1))


@pytest.mark.parametrize("code", ["STALE", "stale data", "", "1stale"])
def test_quality_issue_requires_stable_code(code: str) -> None:
    with pytest.raises(ValueError, match="stable lowercase"):
        QualityIssue(code)


def test_data_quality_keeps_stale_source_time_separate_from_observation_time() -> None:
    observed_at = datetime(2026, 8, 5, 12, tzinfo=UTC)
    data_through = datetime(2026, 8, 4, 18, tzinfo=UTC)

    quality = DataQuality(
        authority=Authority.AUTHORITATIVE,
        completeness=Completeness.PARTIAL,
        observed_at=observed_at,
        data_through=data_through,
        settlement=SettlementState.PENDING,
        issues=(QualityIssue("source.stale"),),
    )

    assert quality.observed_at == observed_at
    assert quality.data_through == data_through
    assert quality.issues == (QualityIssue("source.stale"),)


def test_duplicate_quality_issues_are_rejected() -> None:
    now = datetime.now(UTC)
    issue = QualityIssue("source.stale")

    with pytest.raises(ValueError, match="duplicated"):
        DataQuality(
            authority=Authority.RECONSTRUCTED,
            completeness=Completeness.UNKNOWN,
            observed_at=now,
            issues=(issue, issue),
        )
