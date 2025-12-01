from __future__ import annotations

from collections.abc import Iterable

from stvpoll.abcs import STVPollBase
from stvpoll.base import calculate_stv
from stvpoll.quotas import droop_quota, Quota
from stvpoll.result import ElectionResult
from stvpoll.tiebreak_strategies import (
    TiebreakHistory,
    TiebreakRandom,
    TiebreakStrategy,
)
from stvpoll.transfer_strategies import transfer_serial, TransferStrategy
from stvpoll.types import Candidate, Candidates, SelectionMethod


class ScottishSTV(STVPollBase):
    def __init__(
        self,
        seats,
        candidates,
        quota=droop_quota,
        random_in_tiebreaks=True,
        pedantic_order=False,
    ):
        super().__init__(seats, candidates, quota, random_in_tiebreaks, pedantic_order)

    def calculate_round(self) -> None:
        # First, declare winners if any are over quota
        winners = tuple(
            c for c in self.standing_candidates if self.current_votes[c] >= self.quota
        )
        if winners:
            order = self.elect(
                winners,
                SelectionMethod.Direct,
            )
            # Transfer winning votes in order
            self.transfer_votes(order, decrease_value=True)

        # In case of vote exhaustion, this is theoretically possible.
        elif self.seats_to_fill == len(self.standing_candidates):
            self.elect(
                self.standing_candidates,
                SelectionMethod.NoCompetition,
            )

        # Else exclude a candidate
        else:
            candidate, method = self.get_candidate(most_votes=False)
            self.exclude(candidate, method)
            self.transfer_votes(candidate)


def calculate_scottish_stv(
    candidates: Candidates,
    votes: Iterable[tuple[Iterable[Candidate], int]],
    winners: int,
    *,
    allow_random: bool = True,
    pedantic_order: bool = False,
    random_shuffle: bool = True,
    tiebreak_strategies: tuple[TiebreakStrategy, ...] = None,
    transfer_strategy: TransferStrategy = transfer_serial,
    quota_method: Quota = droop_quota,
) -> ElectionResult:
    """
    :param candidates: All candidates - ballots may not have other candidates
    :param votes: All ballots, with count for each ballot
    :param winners: Number of winners
    :param allow_random: Use random tiebreaking mechanism (recommended)
    :param pedantic_order: Use tiebreaking mechanism for election order of candidates above quota
    :param random_shuffle: If False: Use incoming candidate order instead of shuffling
    :param tiebreak_strategies: Allows overriding tiebreak strategies
    :param transfer_strategy: Defaults to serial transfer
    :param quota_method: Defaults to droop_quota
    :return: Election result
    """
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
        votes,
        winners,
        transfer_strategy=transfer_strategy,
        pedantic_order=pedantic_order,
        quota_method=quota_method,
        tiebreak_strategies=tiebreak_strategies,
    )
