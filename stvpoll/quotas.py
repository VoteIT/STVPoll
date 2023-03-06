from decimal import Decimal
from math import floor


# Used in CPO STV
def hagenbach_bischof_quota(ballot_count: int, winners: int) -> int:
    return int(floor(Decimal(ballot_count) / (winners + 1)))


# Used in Scottish STV
def droop_quota(ballot_count: int, winners: int) -> int:
    return hagenbach_bischof_quota(ballot_count, winners) + 1


# Not used at this time
def hare_quota(ballot_count: int, winners: int) -> int:  # pragma: no coverage
    return int(floor(Decimal(ballot_count) / winners))
