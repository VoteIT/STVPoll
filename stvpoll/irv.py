from .abcs import STVPollBase
from .base import calculate_stv
from .exceptions import IncompleteResult
from .quotas import Quota
from .tiebreak_strategies import TiebreakStrategy, TiebreakHistory, TiebreakRandom
from .transfer_strategies import TransferStrategy, transfer_serial
from .types import BallotData, Candidates, SelectionMethod


def irv_quota(ballot_count: int, winners: int) -> int:
    """
    More than 50 % of votes. This will ignore empty ballots.
    >>> irv_quota(50, 0)
    26
    >>> irv_quota(49, 0)
    25
    """
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


def calculate_irv(
    candidates: Candidates,
    ballots: BallotData,
    *,
    allow_random: bool = True,
    random_shuffle: bool = True,
    tiebreak_strategies: tuple[TiebreakStrategy, ...] = None,
    transfer_strategy: TransferStrategy = transfer_serial,
    quota_method: Quota = irv_quota,
):
    if tiebreak_strategies is None:
        tiebreak_strategies = (
            (
                TiebreakHistory(),
                TiebreakRandom(candidates=candidates, shuffle=random_shuffle),
            )
            if allow_random
            else (TiebreakHistory(),)
        )
    return calculate_stv(
        candidates,
        ballots,
        1,
        elect_last_standing=False,
        tiebreak_strategies=tiebreak_strategies,
        transfer_strategy=transfer_strategy,
        quota_method=quota_method,
    )
