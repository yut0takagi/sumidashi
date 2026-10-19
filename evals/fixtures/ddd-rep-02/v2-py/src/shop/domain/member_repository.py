from abc import ABC, abstractmethod

from sqlalchemy import Select
from sqlalchemy.orm import Session

from shop.domain.member import Member


class MemberRepository(ABC):
    @abstractmethod
    def get(self, member_id: str) -> Member: ...

    @abstractmethod
    def find_by_query(self, stmt: Select) -> list[Member]: ...

    @abstractmethod
    def save(self, member: Member, session: Session) -> None: ...
