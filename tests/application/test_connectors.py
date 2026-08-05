from datetime import UTC, datetime, timedelta
from hashlib import sha256

import pytest

from portfolio_manager.application import (
    AuthenticationState,
    AuthenticationStatus,
    Capability,
    CapabilityOutcome,
    Checkpoint,
    CollectionRequest,
    CollectionResult,
    Connector,
    ConnectorDescriptor,
    ConnectorError,
    ConnectorFailureKind,
    ConnectorIssue,
    NormalizationResult,
    Normalizer,
    OutcomeStatus,
    RawArtifact,
)
from portfolio_manager.domain import BrokerConnectionId, TenantId

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


def artifact(payload: bytes = b'{"safe":"fixture"}') -> RawArtifact:
    return RawArtifact.from_payload(
        payload,
        "application/json",
        NOW,
        "synthetic",
        "v1",
    )


def test_descriptor_requires_stable_versioned_capabilities() -> None:
    descriptor = ConnectorDescriptor("synthetic", "v1", frozenset({Capability.HOLDINGS}))

    assert descriptor.capabilities == frozenset({Capability.HOLDINGS})

    with pytest.raises(ValueError, match="at least one"):
        ConnectorDescriptor("synthetic", "v1", frozenset())


def test_non_ready_authentication_requires_safe_reason() -> None:
    with pytest.raises(ValueError, match="safe reason"):
        AuthenticationState(AuthenticationStatus.EXPIRED)

    state = AuthenticationState(AuthenticationStatus.EXPIRED, "session.expired")
    assert state.reason_code == "session.expired"


def test_ready_authentication_can_have_expiry_but_no_failure_reason() -> None:
    state = AuthenticationState(AuthenticationStatus.READY, expires_at=NOW)
    assert state.expires_at == NOW

    with pytest.raises(ValueError, match="cannot have"):
        AuthenticationState(AuthenticationStatus.READY, "unexpected")


def test_collection_request_is_explicitly_tenant_scoped_and_idempotent() -> None:
    request = CollectionRequest(
        TenantId.new(),
        BrokerConnectionId.new(),
        frozenset({Capability.BALANCES}),
        "daily-2026-08-05",
    )

    assert request.tenant_id is not None
    assert request.idempotency_key == "daily-2026-08-05"


def test_checkpoint_value_is_opaque_and_hidden_from_repr() -> None:
    checkpoint = Checkpoint("v1", b"secret-provider-cursor")

    assert "secret-provider-cursor" not in repr(checkpoint)


def test_raw_artifact_verifies_digest_and_hides_payload() -> None:
    item = artifact()

    assert item.content_digest == sha256(item.payload).hexdigest()
    assert "safe" not in repr(item)

    with pytest.raises(ValueError, match="does not match"):
        RawArtifact(
            b"payload",
            "application/json",
            NOW,
            "synthetic",
            "v1",
            "0" * 64,
        )


def test_collection_result_supports_partial_success() -> None:
    result = CollectionResult(
        (artifact(),),
        (
            CapabilityOutcome(Capability.HOLDINGS, OutcomeStatus.SUCCEEDED),
            CapabilityOutcome(
                Capability.BALANCES,
                OutcomeStatus.PARTIAL,
                (ConnectorIssue("source.incomplete"),),
            ),
        ),
        Checkpoint("v1", b"next"),
    )

    assert result.outcomes[1].status is OutcomeStatus.PARTIAL


def test_collection_result_rejects_duplicate_capabilities() -> None:
    outcome = CapabilityOutcome(Capability.HOLDINGS, OutcomeStatus.SUCCEEDED)
    with pytest.raises(ValueError, match="repeat"):
        CollectionResult((artifact(),), (outcome, outcome))


def test_non_success_outcome_requires_issue() -> None:
    with pytest.raises(ValueError, match="requires an issue"):
        CapabilityOutcome(Capability.HOLDINGS, OutcomeStatus.FAILED)


def test_connector_error_exposes_only_typed_safe_information() -> None:
    error = ConnectorError(
        ConnectorFailureKind.RATE_LIMIT,
        "provider.rate_limit",
        retry_after=timedelta(seconds=10),
    )

    assert str(error) == "rate_limit:provider.rate_limit"
    assert error.retry_after == timedelta(seconds=10)


class FakeConnector:
    async def describe(self) -> ConnectorDescriptor:
        return ConnectorDescriptor("synthetic", "v1", frozenset({Capability.HOLDINGS}))

    async def authentication_state(self) -> AuthenticationState:
        return AuthenticationState(AuthenticationStatus.READY)

    async def collect(self, request: CollectionRequest) -> CollectionResult:
        return CollectionResult(
            (artifact(),),
            (CapabilityOutcome(Capability.HOLDINGS, OutcomeStatus.SUCCEEDED),),
        )


class FakeNormalizer:
    schema_version = "v1"

    def normalize(self, artifact: RawArtifact) -> NormalizationResult:
        return NormalizationResult(())


def test_protocols_allow_structural_third_party_implementations() -> None:
    assert isinstance(FakeConnector(), Connector)
    assert isinstance(FakeNormalizer(), Normalizer)
