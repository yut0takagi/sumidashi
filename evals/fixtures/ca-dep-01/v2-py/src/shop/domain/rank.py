from enum import Enum

from ..application.settings import RANK_THRESHOLDS


class Rank(Enum):
    REGULAR = "regular"
    SILVER = "silver"
    GOLD = "gold"


def rank_for_points(points: int) -> Rank:
    for rank, threshold in reversed(RANK_THRESHOLDS):
        if points >= threshold:
            return Rank(rank)
    return Rank.REGULAR
