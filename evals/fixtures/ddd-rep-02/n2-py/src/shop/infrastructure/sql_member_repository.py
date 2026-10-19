from sqlalchemy import select
from sqlalchemy.orm import Session

from shop.domain.member import Member, MemberFilter


class SqlMemberRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, member_id: str) -> Member:
        return self._session.get(Member, member_id)

    def list(self, filter: MemberFilter) -> list[Member]:
        return list(self._session.scalars(select(Member)))

    def save(self, member: Member) -> None:
        self._session.add(member)
