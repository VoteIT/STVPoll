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
            # FIXME: There is a possibility that there are ties that should be resolved to get the order "right".
            # There is also a theoretical possibility that the order of vote transfers can affect the order,
            # although unlikely.
            self.select_multiple(
                sorted(winners, key=lambda c: c.votes, reverse=True),
                ElectionRound.SELECTION_METHOD_DIRECT)

        # If there there are winner votes to transfer, then do that.
        transfers = [c for c in self.result.elected if not c.votes_transferred]
        if transfers:
            candidate = transfers[0]
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
