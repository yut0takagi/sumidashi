import uuid

from fastapi import Request

from members.domain.member import Member
from members.domain.repository import MemberRepository


class RegisterMember:
    def __init__(self, members: MemberRepository) -> None:
        self._members = members

    async def execute(self, request: Request) -> Member:
        payload = await self._payload(request)
        member = Member(member_id=str(uuid.uuid4()), email=payload["email"])
        self._members.add(member)
        return member

    async def _payload(self, request: Request) -> dict:
        return await request.json()
