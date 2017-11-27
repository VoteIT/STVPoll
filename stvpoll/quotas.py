# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal
from math import floor

from stvpoll import STVPollBase


# Used in CPO STV
def hagenbach_bischof_quota(poll):
    # type: (STVPollBase) -> int
    return int(floor(Decimal(poll.ballot_count) / (poll.seats + 1)))


# Used in Scottish STV
def droop_quota(poll):
    # type: (STVPollBase) -> int
    return hagenbach_bischof_quota(poll) + 1


# Not used at this time
def hare_quota(poll):  # pragma: no coverage
    # type: (STVPollBase) -> int
    return int(floor(Decimal(poll.ballot_count) / poll.seats))
