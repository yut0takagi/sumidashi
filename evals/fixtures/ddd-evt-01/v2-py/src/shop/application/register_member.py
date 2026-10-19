import uuid

from shop.domain.events import DomainEvent, MemberRegister


def register_member(email: str, publish) -> str:
    member_id = str(uuid.uuid4())
    event: DomainEvent = MemberRegister(member_id=member_id, email=email)
    publish(event)
    return member_id
