from shop.domain.member import Member


def promote(member: Member) -> None:
    member.rank = "gold"
