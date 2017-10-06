from decimal import Decimal

from stvpoll import STVPollBase
from stvpoll import Candidate
from stvpoll import ElectionRound


class ScottishSTV(STVPollBase):

    @staticmethod
    def round(value):
        # type: (Decimal) -> Decimal
        return value.quantize(Decimal('.00001'))

    def calculate_round(self, quota):
        # type: () -> None
        candidate, method = self.get_candidate()
        if candidate.votes >= quota:
            self.select(candidate, method)
            transfer_quota = ScottishSTV.round((candidate.votes - quota) / candidate.votes)
            self.result.exhausted += self.transfer_votes(transfer_quota=transfer_quota, candidate=candidate)

        elif self.seats_to_fill == len(self.still_running):
            self.select(candidate, ElectionRound.SELECTION_METHOD_NO_COMPETITION)

        else:
            candidate, method = self.get_candidate(most_votes=False)
            self.select(candidate, method, Candidate.EXCLUDED)
            self.result.exhausted += self.transfer_votes(candidate=candidate)
