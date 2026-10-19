from typing import Protocol

from members.domain.member import Member


class MemberRepository(Protocol):
    def add(self, member: Member) -> None: ...

    def all(self) -> list[Member]: ...
