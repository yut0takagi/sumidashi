from shop.domain.member import Member


class SqlMemberRepository:
    def __init__(self, session) -> None:
        self._session = session

    def add(self, member: Member) -> None:
        self._session.add(member)
