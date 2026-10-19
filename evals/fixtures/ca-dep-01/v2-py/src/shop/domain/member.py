from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from shop.domain.rank import Rank, rank_for_points
from shop.infrastructure.mailer import (
    SmtpMailer,
    MailTemplate,
)


@dataclass
class Member:
    member_id: str
    joined_on: date
    points: int = 0
    rank: Rank = field(default=Rank.REGULAR)

    def add_points(self, points: int, mailer: SmtpMailer) -> None:
        self.points += points
        new_rank = rank_for_points(self.points)
        if new_rank != self.rank:
            self.rank = new_rank
            mailer.send(MailTemplate.RANK_UP, to=self.member_id)
