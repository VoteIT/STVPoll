from __future__ import annotations

from decimal import Decimal
from itertools import combinations
from math import factorial
import random

from typing import Iterable

from .abcs import STVPollBase
from .exceptions import IncompleteResult
from .quotas import (
    Quota,
    hagenbach_bischof_quota,
)
from .types import (
    SelectionMethod,
    CandidateStatus,
    Candidates,
    Candidate,
)


class CPOComparisonPoll(STVPollBase):
    def __init__(
        self,
        seats: int,
        candidates: Iterable,
        winners: set[Candidate],
        compared: set[Candidate],
        quota: Quota = hagenbach_bischof_quota,
    ):
        super(CPOComparisonPoll, self).__init__(seats, candidates, quota)
        self.compared = compared
        self.winners = winners
        self.below_quota = False

    def do_rounds(self) -> None:
        for exclude in set(self.standing_candidates).difference(self.winners):
            self.exclude(exclude, SelectionMethod.Direct)
            self.transfer_votes(exclude)

        elected = tuple(set(self.standing_candidates).difference(self.compared))
        self.elect(elected, SelectionMethod.Direct)
        self.transfer_votes(elected, decrease_value=True)

    @property
    def not_excluded(self) -> Candidates:
        excluded = tuple(
            r.selected[0]
            for r in self.result.rounds
            if r.status == CandidateStatus.Excluded
        )
        return tuple(c for c in self.candidates if c not in excluded)

    def total_except(self, candidates: Candidates) -> Decimal:
        return sum(
            self.get_current_votes(c) for c in self.not_excluded if c not in candidates
        )


class CPOComparisonResult:
    def __init__(
        self,
        poll: CPOComparisonPoll,
        compared: tuple[tuple[Candidate], tuple[Candidate]],
    ) -> None:
        self.poll = poll
        self.compared = compared
        self.all = set(compared[0] + compared[1])
        self.totals = sorted(
            (
                (compared[0], self.total(compared[0])),
                (compared[1], self.total(compared[1])),
            ),
            key=lambda c: c[1],
        )
        # May be unclear here, but winner or looser does not matter if tied
        self.loser, self.winner = [c[0] for c in self.totals]
        self.difference = self.totals[1][1] - self.totals[0][1]
        self.tied = self.difference == 0

    def others(self, combination: tuple[Candidate]) -> set[Candidate]:
        return self.all.difference(combination)

    def total(self, combination: tuple[Candidate]) -> Decimal:
        return self.poll.total_except(list(self.others(combination)))


class CPO_STV(STVPollBase):
    def __init__(self, quota=hagenbach_bischof_quota, *args, **kwargs):
        self.random_in_tiebreaks = kwargs.get("random_in_tiebreaks", True)
        kwargs["pedantic_order"] = False
        super(CPO_STV, self).__init__(*args, quota=quota, **kwargs)

    @staticmethod
    def possible_combinations(proposals: int, winners: int) -> int:
        return int(
            factorial(proposals) / factorial(winners) / factorial(proposals - winners)
        )

    def get_best_approval(self) -> list[Candidate]:
        # If no more seats to fill, there will be no duels. Return empty list.
        if self.seats_to_fill == 0:
            return []

        duels = []
        possible_outcomes = list(
            combinations(self.standing_candidates, self.seats_to_fill)
        )
        for combination in combinations(possible_outcomes, 2):
            compared = set(c for sublist in combination for c in sublist)
            winners = set(compared)
            winners.update(self.result)
            comparison_poll = CPOComparisonPoll(
                self.seats, self.candidates, winners=winners, compared=compared
            )

            for ballot in self.ballots:
                comparison_poll.add_ballot(ballot, ballot.count)

            comparison_poll.calculate()
            duels.append(CPOComparisonResult(comparison_poll, combination))

        # Return either a clear winner (no ties), or resolved using MiniMax
        return self.get_duels_winner(duels) or self.resolve_tie_minimax(duels)
        # ... Ranked Pairs (so slow)
        # return self.get_duels_winner(duels) or self.resolve_tie_ranked_pairs(duels)

    def get_duels_winner(self, duels: list[CPOComparisonResult]) -> list[Candidate]:
        wins = set()
        losses = set()
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
        # No clear winner
        return []

    def resolve_tie_minimax(self, duels: list[CPOComparisonResult]) -> list[Candidate]:
        from tarjan import tarjan

        graph = {}
        for d in duels:
            graph.setdefault(d.loser, []).append(d.winner)
            if d.tied:
                graph.setdefault(d.winner, []).append(d.loser)
        smith_set = tarjan(graph)[0]

        biggest_defeats = {}
        for candidates in smith_set:
            ds = filter(
                lambda d: d.loser == candidates or (d.tied and d.winner == candidates),
                duels,
            )
            biggest_defeats[candidates] = max(d.difference for d in ds)
        minimal_defeat = min(biggest_defeats.values())
        equals = [
            candidates
            for candidates, diff in biggest_defeats.items()
            if diff == minimal_defeat
        ]
        if len(equals) == 1:  # pragma: no cover
            return equals[0]
        if not self.random_in_tiebreaks:
            raise IncompleteResult("Random in tiebreaks disallowed")
        self.result.set_randomized()
        return random.choice(equals)

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

    def do_rounds(self) -> None:
        if len(self.candidates) == self.seats:
            self.elect(self.candidates, SelectionMethod.Direct)
            return

        self.elect(
            tuple(c for c in self.candidates if self.get_current_votes(c) > self.quota),
            SelectionMethod.Direct,
        )

        self.elect(tuple(self.get_best_approval()), SelectionMethod.CPO)
