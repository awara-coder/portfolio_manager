"""Opaque identifiers for broker-neutral domain entities."""

from dataclasses import dataclass
from typing import Self
from uuid import UUID, uuid4


class TenantTag:
    pass


class UserTag:
    pass


class BrokerConnectionTag:
    pass


class BrokerAccountTag:
    pass


class ExternalCashAccountTag:
    pass


class InstitutionTag:
    pass


class InstrumentTag:
    pass


class ListingTag:
    pass


class SourceRecordTag:
    pass


class CollectionRunTag:
    pass


class RawArtifactTag:
    pass


class ActivityTag:
    pass


class TransferTag:
    pass


class ObservationTag:
    pass


class SnapshotTag:
    pass


class ReportTag:
    pass


@dataclass(frozen=True, slots=True, order=True)
class Identifier[EntityTag]:
    value: UUID

    @classmethod
    def new(cls) -> Self:
        return cls(uuid4())

    @classmethod
    def parse(cls, value: str) -> Self:
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)


TenantId = Identifier[TenantTag]
UserId = Identifier[UserTag]
BrokerConnectionId = Identifier[BrokerConnectionTag]
BrokerAccountId = Identifier[BrokerAccountTag]
ExternalCashAccountId = Identifier[ExternalCashAccountTag]
InstitutionId = Identifier[InstitutionTag]
InstrumentId = Identifier[InstrumentTag]
ListingId = Identifier[ListingTag]
SourceRecordId = Identifier[SourceRecordTag]
CollectionRunId = Identifier[CollectionRunTag]
RawArtifactId = Identifier[RawArtifactTag]
ActivityId = Identifier[ActivityTag]
TransferId = Identifier[TransferTag]
ObservationId = Identifier[ObservationTag]
SnapshotId = Identifier[SnapshotTag]
ReportId = Identifier[ReportTag]
