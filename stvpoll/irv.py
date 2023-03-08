from decimal import Decimal
from math import floor

from .abcs import STVPollBase
from .exceptions import IncompleteResult
from .types import SelectionMethod


def irv_quota(ballot_count: int, winners: int) -> int:
    """More than 50 % of votes. This will ignore empty ballots."""
    return int(floor(Decimal(ballot_count) / 2)) + 1


class IRV(STVPollBase):
    multiple_winners = False

    def __init__(self, **kwargs):
        kwargs.setdefault("quota", irv_quota)
        kwargs["seats"] = 1
        super().__init__(**kwargs)

    def calculate_round(self) -> None:
        # First, check if there is a winner
        for proposal in self.standing_candidates:
            if self.get_current_votes(proposal) >= self.quota:
                return self.elect(proposal, SelectionMethod.Direct)

        if len(self.standing_candidates) == 1:
            raise IncompleteResult("No candidate can get majority.")

        loser, method = self.get_candidate(most_votes=False)
        self.exclude(loser, method)
        self.transfer_votes(loser)
