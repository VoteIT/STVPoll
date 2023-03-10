from __future__ import annotations

from stvpoll.abcs import STVPollBase
from stvpoll.quotas import droop_quota
from stvpoll.types import SelectionMethod


class ScottishSTV(STVPollBase):
    def __init__(
        self,
        seats,
        candidates,
        quota=droop_quota,
        random_in_tiebreaks=True,
        pedantic_order=False,
    ):
        super(ScottishSTV, self).__init__(
            seats, candidates, quota, random_in_tiebreaks, pedantic_order
        )

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
