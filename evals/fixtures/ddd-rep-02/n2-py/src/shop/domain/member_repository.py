from typing import Protocol

from shop.domain.member import Member, MemberFilter


class MemberRepository(Protocol):
    def get(self, member_id: str) -> Member: ...

    def list(self, filter: MemberFilter) -> list[Member]: ...

    def save(self, member: Member) -> None: ...
