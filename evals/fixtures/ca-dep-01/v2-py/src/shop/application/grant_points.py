from shop.domain.member import Member


def grant_points(member: Member, points: int, mailer) -> None:
    member.add_points(points, mailer)
