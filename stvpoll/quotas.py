from decimal import Decimal
from math import floor

from stvpoll.abcs import STVPollBase


# Used in CPO STV
def hagenbach_bischof_quota(poll: STVPollBase) -> int:
    return int(floor(Decimal(poll.ballot_count) / (poll.seats + 1)))


# Used in Scottish STV
def droop_quota(poll: STVPollBase) -> int:
    return hagenbach_bischof_quota(poll) + 1


# Not used at this time
def hare_quota(poll: STVPollBase) -> int:  # pragma: no coverage
    return int(floor(Decimal(poll.ballot_count) / poll.seats))
