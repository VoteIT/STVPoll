from decimal import Decimal
from math import floor
from typing import Protocol


class Quota(Protocol):
    """Calculate poll quota from valid ballot count and expected poll winners"""

    def __call__(self, ballot_count: int, winners: int) -> int:  # pragma: no coverage
        ...


# Used in CPO STV
def hagenbach_bischof_quota(ballot_count: int, winners: int) -> int:
    return int(floor(Decimal(ballot_count) / (winners + 1)))


# Used in Scottish STV
def droop_quota(ballot_count: int, winners: int) -> int:
    return hagenbach_bischof_quota(ballot_count, winners) + 1


# Not used at this time
def hare_quota(ballot_count: int, winners: int) -> int:  # pragma: no coverage
    return int(floor(Decimal(ballot_count) / winners))
