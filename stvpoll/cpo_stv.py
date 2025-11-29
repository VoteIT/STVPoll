from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from itertools import combinations
from math import factorial
import random

from tarjan import tarjan

from .abcs import STVPollBase, PreferenceBallot
from .exceptions import IncompleteResult
from .quotas import droop_quota
from .types import SelectionMethod, Candidates, Candidate


@dataclass
class CPOComparisonPoll:
    ballots: tuple[PreferenceBallot, ...]
    compared: tuple[Candidates, Candidates]
    quota: int

    def candidate_ballots(self, candidate: Candidate) -> Iterator[PreferenceBallot]:
        """Yields ballots where candidate is currently on top"""
        for b in self.ballots:
            if b.get_next_preference(self.standing) == candidate:
                yield b

    def __post_init__(self) -> None:
        """Perform comparison here"""
        outcome1, outcome2 = set(self.compared[0]), set(self.compared[1])
        # Eliminate candidates in neither outcome
        self.standing = outcome1 | outcome2
        # Count initial votes after primary transfers.
        votes = {
            c: Decimal(sum((b.count for b in self.candidate_ballots(c)), start=0))
            for c in self.standing
        }

        # Transfer surpluses of candidates in both outcomes
        for candidate in outcome1 & outcome2:
            if votes[candidate] > self.quota:
                # Set candidates votes to quota and get fraction to transfer
                votes[candidate], transfer_fraction = (
                    self.quota,
                    (votes[candidate] - self.quota) / votes[candidate],
                )
                # Do the actual transfer, according to fraction
                for ballot in self.candidate_ballots(candidate):
                    ballot.decrease_value(transfer_fraction)
                    if next_preference := ballot.get_next_preference(
                        self.standing.difference((candidate,))
                    ):
                        votes[next_preference] += ballot.value
            self.standing.remove(candidate)

        # Add up the totals
        totals = sorted(
            ((outcome, sum(votes[c] for c in outcome)) for outcome in self.compared),
            key=lambda c: c[1],
        )
        # May be unclear here, but winner or loser does not matter if tied
        self.loser = totals[0][0]
        self.winner = totals[1][0]
        self.difference: Decimal = totals[1][1] - totals[0][1]
        self.tied = self.difference == 0


class CPO_STV(STVPollBase):
    def __init__(self, quota=droop_quota, *args, **kwargs):
        self.random_in_tiebreaks = kwargs.get("random_in_tiebreaks", True)
        kwargs["pedantic_order"] = False
        super().__init__(*args, quota=quota, **kwargs)

    def calculate_round(self) -> None:
        """Elect in one round"""
        if len(self.candidates) == self.seats:
            self.elect(self.candidates, SelectionMethod.Direct)
        else:
            self.elect(tuple(self.get_best_approval()), SelectionMethod.CPO)

    @staticmethod
    def possible_combinations(proposals: int, winners: int) -> int:
        """
        >>> CPO_STV.possible_combinations(5, 2)
        10
        """
        return int(
            factorial(proposals) / factorial(winners) / factorial(proposals - winners)
        )

    def get_best_approval(self) -> Candidates:
        possible_outcomes = tuple(
            combinations(self.standing_candidates, self.seats_to_fill)
        )
        duels = tuple(
            CPOComparisonPoll(
                # Copy ballots to ensure no manipulation of originals
                ballots=tuple(
                    PreferenceBallot(tuple(b), b.count) for b in self.ballots
                ),
                compared=combination,
                quota=self.quota,
            )
            for combination in combinations(possible_outcomes, 2)
        )

        # Return either a clear winner (no ties), or resolved using MiniMax
        return self.get_duels_winner(duels) or self.resolve_tie_minimax(duels)
        # ... Ranked Pairs (so slow)
        # return self.get_duels_winner(duels) or self.resolve_tie_ranked_pairs(duels)

    @staticmethod
    def get_duels_winner(duels: tuple[CPOComparisonPoll, ...]) -> Candidates | None:
        wins = set[Candidates]()
        losses = set[Candidates]()
        for duel in duels:
            losses.add(duel.loser)
            if duel.tied:
                losses.add(duel.winner)
            else:
                wins.add(duel.winner)

        undefeated = wins - losses
        if len(undefeated) == 1:
            # If there is ONE clear winner (won all duels), return that combination.
            return undefeated.pop()

    def resolve_tie_minimax(self, duels: tuple[CPOComparisonPoll, ...]) -> Candidates:
        graph = defaultdict(list)
        for d in duels:
            graph[d.loser].append(d.winner)
            if d.tied:
                graph[d.winner].append(d.loser)

        # The smith set is a set of winners at the top-cycle, when there is no Condorcet winner.
        smith_set: list[Candidates] = tarjan(graph)[0]

        biggest_defeats = {
            candidates: max(
                (duel.difference for duel in duels if duel.loser == candidates),
                default=Decimal(0),
            )
            for candidates in smith_set
        }
        minimal_defeat = min(biggest_defeats.values())
        winners = [
            candidates
            for candidates, diff in biggest_defeats.items()
            if diff == minimal_defeat
        ]
        if len(winners) == 1:  # pragma: no cover
            return winners[0]
        if not self.random_in_tiebreaks:
            raise IncompleteResult("Random in tiebreaks disallowed")
        self.result.set_randomized()
        return random.choice(winners)

    # def resolve_tie_ranked_pairs(self, duels):
    #     # type: (List[CPOComparisonResult]) -> List[Candidate]
    #     # https://medium.com/freds-blog/explaining-the-condorcet-system-9b4f47aa4e60
    #     class TracebackFound(STVException):
    #         pass
    #
    #     def traceback(duel, _trace=None):
    #         # type: (CPOComparisonResult, CPOComparisonResult) -> None
    #         for trace in filter(lambda d: d.winner == (_trace and _trace.loser or duel.loser), noncircular_duels):
    #             if duel.winner == trace.loser:
    #                 raise TracebackFound()
    #             traceback(duel, trace)
    #
    #     difference_groups = {}
    #     # filter: Can't declare winners if duel was tied.
    #     for d in filter(lambda d: not d.tied, duels):
    #         try:
    #             difference_groups[d.difference].append(d)
    #         except KeyError:
    #             difference_groups[d.difference] = [d]
    #
    #     noncircular_duels = []
    #
    #     # Check if there are equal difference duels
    #     # Need to make sure these do not cause tiebreaks depending on order
    #     for difference in sorted(difference_groups.keys(), reverse=True):
    #         saved_list = noncircular_duels[:]
    #         group = difference_groups[difference]
    #         try:
    #             for duel in group:
    #                 traceback(duel)
    #                 noncircular_duels.append(duel)
    #         except TracebackFound:
    #             if len(group) > 1:
    #                 noncircular_duels = saved_list
    #                 while group:
    #                     duel = self.choice(group)
    #                     try:
    #                         traceback(duel)
    #                         noncircular_duels.append(duel)
    #                     except TracebackFound:
    #                         pass
    #                     group.remove(duel)
    #
    #     return self.get_duels_winner(noncircular_duels)
