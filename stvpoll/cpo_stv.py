from collections import Counter
from decimal import Decimal
from itertools import combinations

from stvpoll.exceptions import STVException
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

    # def transfer_votes(self, candidate, transfer_quota=Decimal(1)):
    #     super(CPOComparisonPoll, self).transfer_votes(candidate, transfer_quota)
    #     if candidate.votes > self.quota:
    #         candidate.votes = self.quota

    # def select_round(self, candidate, status=Candidate.ELECTED):
    #     # type: (Candidate, int) -> None
    #     candidate = [c for c in self.candidates if c == candidate][0]
    #     self.select(candidate, ElectionRound.SELECTION_METHOD_CPO, status)
    #     transfer_quota = status == Candidate.ELECTED and (candidate.votes - self.quota) / candidate.votes or 1
    #     self.transfer_votes(candidate, transfer_quota=transfer_quota)

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
        # TODO Implement random for extreme cases? (Now decided by position in list below)
        self.totals = sorted((
            (compared[0], self.total(compared[0])),
            (compared[1], self.total(compared[1])),
        ), key=lambda c: c[1])
        self.looser, self.winner = [c[0] for c in self.totals]
        self.difference = self.totals[1][1] - self.totals[0][1]

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

    def __init__(self, seats, candidates, quota=hagenbach_bischof_quota):
        super(CPO_STV, self).__init__(seats, candidates, quota)

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
        wins = Counter()
        losses = Counter()
        for duel in duels:
            wins[duel.winner] += 1
            losses[duel.looser] += 1
        winner = wins.most_common()[0][0]
        # If there is a clear winner (won all duels), return that combination.
        if winner not in losses:
            return winner

    def resolve_tie_ranked_pairs(self, duels):
        # type: (List[CPOComparisonResult]) -> List[Candidate]
        # https://medium.com/freds-blog/explaining-the-condorcet-system-9b4f47aa4e60
        class TracebackFound(STVException):
            pass

        noncircular_duels = []

        def traceback(duel, _trace=None):
            # type: (CPOComparisonResult, CPOComparisonResult) -> None
            for trace in filter(lambda d: d.winner == (_trace and _trace.looser or duel.looser), noncircular_duels):
                if duel.winner == trace.looser:
                    raise TracebackFound()
                traceback(duel, trace)

        for duel in sorted(duels, key=lambda d: d.difference, reverse=True):
            try:
                traceback(duel)
                noncircular_duels.append(duel)
            except TracebackFound:
                pass

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
