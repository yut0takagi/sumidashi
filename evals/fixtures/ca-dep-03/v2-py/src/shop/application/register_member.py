import uuid

from shop.domain.member import Member
from shop.infrastructure.repositories import SqlMemberRepository
from ..adapters.api.schemas import MemberResponse


class RegisterMember:
    def __init__(self, members: SqlMemberRepository) -> None:
        self._members = members

    def execute(self, email: str) -> MemberResponse:
        member = Member(member_id=str(uuid.uuid4()), email=email)
        self._members.add(member)
        return MemberResponse(id=member.member_id, email=member.email)
