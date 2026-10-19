from dataclasses import dataclass


@dataclass(frozen=True)
class MemberFilter:
    rank: str | None = None
    joined_after: str | None = None


class Member:
    def __init__(self, member_id: str, rank: str) -> None:
        self._id = member_id
        self._rank = rank
