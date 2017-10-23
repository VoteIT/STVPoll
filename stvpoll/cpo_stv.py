from __future__ import unicode_literals

from decimal import Decimal
from random import choice
from itertools import combinations
from math import factorial

from stvpoll.exceptions import STVException, IncompleteResult
from typing import Iterable
from typing import List

from stvpoll import Candidate
from stvpoll import ElectionRound
from stvpoll import STVPollBase
from stvpoll import hagenbach_bischof_quota


class CPOComparisonPoll(STVPollBase):

    def __init__(self, seats, candidates, quota=hagenbach_bischof_quota, winners=(), compared=()):
        super(CPOComparisonPoll, self).__init__(seats, [c.obj for c in candidates], quota)
        self.compared = [self.get_existing_candidate(c.obj) for c in compared]
        self.winners = [self.get_existing_candidate(c.obj) for c in winners]
        self.below_quota = False

    def do_rounds(self):
        # type: () -> None
        for exclude in set(self.still_running).difference(self.winners):
            self.select(exclude, ElectionRound.SELECTION_METHOD_DIRECT, Candidate.EXCLUDED)
            self.transfer_votes(exclude)

        for transfer in set(self.still_running).difference(self.compared):
            self.select(transfer, ElectionRound.SELECTION_METHOD_DIRECT)
            self.transfer_votes(transfer, transfer_quota=(Decimal(transfer.votes) - self.quota) / transfer.votes)
            transfer.votes = self.quota

    @property
    def not_excluded(self):
        # type: () -> List[Candidate]
        return list(filter(lambda c: c.status != Candidate.EXCLUDED, self.candidates))

    def total_except(self, candidates):
        # type: (List[Candidate]) -> Decimal
        return sum([c.votes for c in self.not_excluded if c not in candidates])


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

    def get_combination(self, winning):
        # type: (bool) -> List[Candidate]
        return sorted(self.totals, key=lambda x: x[1])[winning and 1 or 0][0]

    def total(self, combination):
        # type: (List[Candidate]) -> Decimal
        return self.poll.total_except(list(self.others(combination)))


class CPO_STV(STVPollBase):

    def __init__(self, quota=hagenbach_bischof_quota, *args, **kwargs):
        super(CPO_STV, self).__init__(*args, quota=quota, **kwargs)

    @staticmethod
    def possible_combinations(total, limit):
        # type: (int, int) -> int
        return factorial(total) / factorial(limit) / factorial(total - limit)

    def get_best_approval(self):
        # type: (int) -> Iterable[Candidate]
        duels = []

        possible_outcomes = list(combinations(self.still_running, self.seats_to_fill))
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
                comparison_poll.add_ballot([c.obj for c in ballot], self.ballots[ballot])

            comparison_poll.calculate()
            duels.append(CPOComparisonResult(
                comparison_poll,
                combination))

        # Return either a clear winner (no ties), or resolved using Ranked Pairs
        return self.get_duels_winner(duels) or self.resolve_tie_ranked_pairs(duels)

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
            # If there is a clear winner (won all duels), return that combination.
            return undefeated.pop()
        elif len(undefeated) > 1:
            # If there are more than one choice and random is allowed. (Extreme case)
            return self.choice(list(undefeated))
        # No clear winner and no random
        return []

    def resolve_tie_ranked_pairs(self, duels):
        # type: (List[CPOComparisonResult]) -> List[Candidate]
        # https://medium.com/freds-blog/explaining-the-condorcet-system-9b4f47aa4e60
        class TracebackFound(STVException):
            pass

        # Can't declare winners if duel was tied.
        duels = filter(lambda d: not d.tied, duels)
        noncircular_duels = []

        def traceback(duel, _trace=None):
            # type: (CPOComparisonResult, CPOComparisonResult) -> None
            for trace in filter(lambda d: d.winner == (_trace and _trace.loser or duel.loser), noncircular_duels):
                if duel.winner == trace.loser:
                    raise TracebackFound()
                traceback(duel, trace)

        sorted_duels = sorted(duels, key=lambda d: d.difference, reverse=True)
        while len(sorted_duels):
            duel = sorted_duels[0]

            # Check if there are equal difference duels
            # Need to make sure these do not cause tiebreaks depending on order
            equals = filter(lambda d: d.difference == duel.difference, sorted_duels)
            if len(equals) > 1:
                saved_list = noncircular_duels[:]
                try:
                    for eduel in equals:
                        traceback(eduel)
                        noncircular_duels.append(eduel)
                except TracebackFound:
                    if self.random_in_tiebreaks:
                        self.result.randomized = True
                        duel = choice(equals)
                    else:
                        raise IncompleteResult()
                noncircular_duels = saved_list

            try:
                traceback(duel)
                noncircular_duels.append(duel)
            except TracebackFound:
                pass
            sorted_duels.remove(duel)

        return self.get_duels_winner(noncircular_duels)

    def do_rounds(self):
        # type: (int) -> None

        if len(self.candidates) == self.seats:
            self.select_multiple(
                self.candidates,
                ElectionRound.SELECTION_METHOD_DIRECT)
            return

        self.select_multiple(
            filter(lambda c: c.votes > self.quota, self.candidates),
            ElectionRound.SELECTION_METHOD_DIRECT)

        self.select_multiple(
            self.get_best_approval(),
            ElectionRound.SELECTION_METHOD_CPO)
