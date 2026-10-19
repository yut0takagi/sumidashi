from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, kw_only=True)
class PointsGranted(DomainEvent):
    member_id: str
    points: int


@dataclass(frozen=True, kw_only=True)
class MemberRegister(DomainEvent):
    member_id: str
    email: str


@dataclass(frozen=True, kw_only=True)
class RankUpgradeEvent(DomainEvent):
    member_id: str
    new_rank: str


@dataclass(frozen=True, kw_only=True)
class MemberLoggedIn(DomainEvent):
    member_id: str
