from __future__ import unicode_literals

from decimal import Decimal

from stvpoll import STVPollBase
from stvpoll import Candidate
from stvpoll import ElectionRound


class ScottishSTV(STVPollBase):

    @staticmethod
    def round(value):
        # type: (Decimal) -> Decimal
        return value.quantize(Decimal('.00001'))

    def calculate_round(self):
        # type: () -> None
        winners = filter(lambda c: c.votes >= self.quota, self.standing_candidates)
        if winners:
            winners = sorted(winners, key=lambda c: c.votes, reverse=True)
            self.select_multiple(winners, ElectionRound.SELECTION_METHOD_DIRECT)
            for candidate in winners:
                transfer_quota = ScottishSTV.round((candidate.votes - self.quota) / candidate.votes)
                self.transfer_votes(candidate, transfer_quota=transfer_quota)
            return

        # In case of vote exhaustion, this is theoretically possible.
        if self.seats_to_fill == len(self.standing_candidates):
            self.select_multiple(self.standing_candidates, ElectionRound.SELECTION_METHOD_NO_COMPETITION)
            return

        candidate, method = self.get_candidate(most_votes=False)
        self.select(candidate, method, Candidate.EXCLUDED)
        self.transfer_votes(candidate)
