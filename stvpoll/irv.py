from .abcs import STVPollBase
from .exceptions import IncompleteResult
from .types import SelectionMethod


def irv_quota(ballot_count: int, winners: int) -> int:
    """More than 50 % of votes. This will ignore empty ballots."""
    return ballot_count // 2 + 1


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
                self.elect(proposal, SelectionMethod.Direct)
                return

        if len(self.standing_candidates) == 1:
            raise IncompleteResult("No candidate can get majority.")

        # Exclude one candidate
        candidate, method = self.get_candidate(most_votes=False)
        self.exclude(candidate, method)
        self.transfer_votes(candidate)
