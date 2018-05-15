# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import Counter
from decimal import Decimal
from itertools import combinations
from math import factorial

from typing import Iterable
from typing import List

from stvpoll import Candidate
from stvpoll import ElectionRound
from stvpoll import STVPollBase
from stvpoll.quotas import hagenbach_bischof_quota


class CPOComparisonPoll(STVPollBase):

    def __init__(self, seats, candidates, quota=hagenbach_bischof_quota, winners=(), compared=()):
        super(CPOComparisonPoll, self).__init__(seats, [c.obj for c in candidates], quota)
        self.compared = [self.get_existing_candidate(c.obj) for c in compared]
        self.winners = [self.get_existing_candidate(c.obj) for c in winners]
        self.below_quota = False

    def do_rounds(self):
        # type: () -> None
        for exclude in set(self.standing_candidates).difference(self.winners):
            self.select(exclude, ElectionRound.SELECTION_METHOD_DIRECT, Candidate.EXCLUDED)
            self.transfer_votes(exclude)

        for transfer in set(self.standing_candidates).difference(self.compared):
            self.select(transfer, ElectionRound.SELECTION_METHOD_DIRECT)
            self.transfer_votes(transfer, transfer_quota=(Decimal(transfer.votes) - self.quota) / transfer.votes)
            transfer.votes = self.quota

    @property
    def not_excluded(self):
        # type: () -> List[Candidate]
        return [c for c in self.candidates if c.status != Candidate.EXCLUDED]

    def total_except(self, candidates):
        # type: (List[Candidate]) -> Decimal
        return sum(c.votes for c in self.not_excluded if c not in candidates)


class CPOComparisonResult:
    def __init__(self, poll, compared):
        # type: (CPOComparisonPoll, List[List[Candidate]]) -> None
        self.poll = poll
        self.compared = compared
        self.all = set(compared[0] + compared[1])
        self.totals = sorted((
            (compared[0], self.total(compared[0])),
            (compared[1], self.total(compared[1])),
        ), key=lambda c: c[1])
        # May be unclear here, but winner or looser does not matter if tied
        self.loser, self.winner = [c[0] for c in self.totals]
        self.difference = self.totals[1][1] - self.totals[0][1]
        self.tied = self.difference == 0

    def others(self, combination):
        # type: (List[Candidate]) -> Iterable[Candidate]
        return self.all.difference(combination)

    def total(self, combination):
        # type: (List[Candidate]) -> Decimal
        return self.poll.total_except(list(self.others(combination)))


class CPO_STV(STVPollBase):

    def __init__(self, quota=hagenbach_bischof_quota, *args, **kwargs):
        super(CPO_STV, self).__init__(*args, quota=quota, **kwargs)

    @staticmethod
    def possible_combinations(proposals, winners):
        # type: (int, int) -> int
        return factorial(proposals) / factorial(winners) / factorial(proposals - winners)

    def get_best_approval(self):
        # type: () -> List[Candidate]
        duels = []

        possible_outcomes = list(combinations(self.standing_candidates, self.seats_to_fill))
        for combination in combinations(possible_outcomes, 2):
            compared = set([c for sublist in combination for c in sublist])
            winners = set(compared)
            winners.update(self.result.elected)
            comparison_poll = CPOComparisonPoll(
                self.seats,
                self.candidates,
                winners=winners,
                compared=compared)

            for ballot in self.ballots:
                comparison_poll.add_ballot([c.obj for c in ballot.preferences], ballot.count)

            comparison_poll.calculate()
            duels.append(CPOComparisonResult(
                comparison_poll,
                combination))

        # Return either a clear winner (no ties), or resolved using MiniMax
        return self.get_duels_winner(duels) or self.resolve_tie_minimax(duels)
        # ... Ranked Pairs (so slow)
        # return self.get_duels_winner(duels) or self.resolve_tie_ranked_pairs(duels)

    def get_duels_winner(self, duels):
        # type: (List[CPOComparisonResult]) -> List[Candidate]
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

    def resolve_tie_minimax(self, duels):
        # type: (List[CPOComparisonResult]) -> List[Candidate]
        from tarjan import tarjan
        graph = {}
        for d in duels:
            graph.setdefault(d.loser, []).append(d.winner)
            if d.tied:
                graph.setdefault(d.winner, []).append(d.loser)
        smith_set = tarjan(graph)[0]

        biggest_defeats = {}
        for candidates in smith_set:
            ds = filter(lambda d: d.loser == candidates or (d.tied and d.winner == candidates), duels)
            biggest_defeats[candidates] = max(d.difference for d in ds)
        minimal_defeat = min(biggest_defeats.values())
        equals = [defeat[0] for defeat in biggest_defeats.items() if defeat[1] == minimal_defeat]
        if len(equals) > 1:
            return self.choice(equals)
        return equals[0]  # pragma: no cover

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

    def do_rounds(self):
        # type: () -> None

        if len(self.candidates) == self.seats:
            self.select_multiple(
                self.candidates,
                ElectionRound.SELECTION_METHOD_DIRECT)
            return

        self.select_multiple(
            [c for c in self.candidates if c.votes > self.quota],
            ElectionRound.SELECTION_METHOD_DIRECT)

        self.select_multiple(
            list(self.get_best_approval()),
            ElectionRound.SELECTION_METHOD_CPO)
