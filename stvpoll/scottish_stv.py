# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal

from stvpoll import STVPollBase
from stvpoll import Candidate
from stvpoll import ElectionRound
from stvpoll.quotas import droop_quota


class ScottishSTV(STVPollBase):

    def __init__(self, seats, candidates, quota=droop_quota, random_in_tiebreaks=True):
        super(ScottishSTV, self).__init__(seats, candidates, quota, random_in_tiebreaks)

    @staticmethod
    def round(value):
        # type: (Decimal) -> Decimal
        return value.quantize(Decimal('.00001'))

    def calculate_round(self):
        # type: () -> None

        # First, declare winners if any are over quota
        winners = filter(lambda c: c.votes >= self.quota, self.standing_candidates)
        if winners:
            self.select_multiple(
                sorted(winners, key=lambda c: c.votes, reverse=True),
                ElectionRound.SELECTION_METHOD_DIRECT)

        # Are there winner votes to transfer, then do that.
        transfers = filter(lambda c: not c.votes_transferred, self.result.elected)
        if transfers:
            candidate = transfers[0]
            ties = self.get_ties(candidate, transfers)
            if ties:
                candidate, method = self.resolve_tie(ties)

            transfer_quota = ScottishSTV.round((candidate.votes - self.quota) / candidate.votes)
            self.transfer_votes(candidate, transfer_quota=transfer_quota)

        # In case of vote exhaustion, this is theoretically possible.
        elif self.seats_to_fill == len(self.standing_candidates):
            self.select_multiple(self.standing_candidates, ElectionRound.SELECTION_METHOD_NO_COMPETITION)

        # Else exclude a candidate
        else:
            candidate, method = self.get_candidate(most_votes=False)
            self.select(candidate, method, Candidate.EXCLUDED)
            self.transfer_votes(candidate)
