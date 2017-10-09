from collections import Counter
from decimal import Decimal

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
        self.totals = (
            (compared[0], self.total(compared[0])),
            (compared[1], self.total(compared[1])),
        )

    def others(self, combination):
        # type: (List[Candidate]) -> Iterable[Candidate]
        return self.all.difference(combination)

    def get_combination(self, winning):
        # type: (bool) -> List[Candidate]
        fn = winning and max or min
        return fn(self.totals, key=lambda x: x[1])[0]

    @property
    def winner(self):
        # type: (bool) -> List[Candidate]
        return self.get_combination(True)

    @property
    def looser(self):
        # type: (bool) -> List[Candidate]
        return self.get_combination(False)

    @property
    def difference(self):
        return self.total(self.get_combination(True)) - self.total(self.get_combination(False))

    def total(self, combination):
        # type: (List[Candidate]) -> Decimal
        return self.poll.total_except(list(self.others(combination)))


class CPO_STV(STVPollBase):

    def __init__(self, seats, candidates, quota=hagenbach_bischof_quota):
        super(CPO_STV, self).__init__(seats, candidates, quota)

    def get_best_approval(self):
        # type: (int) -> Iterable[Candidate]
        from itertools import combinations
        leader = None
        possible_outcomes = list(combinations(self.still_running, self.seats_to_fill))
        # print('Seats: {}\nPairups: {}\nCandidates: {}\nAlready elected: {}\n\n'.format(
        #     self.seats_to_fill,
        #     len(list(combinations(possible_outcomes, 2))),
        #     map(str, self.still_running),
        #     map(str, self.result.elected),
        # ))
        wins = Counter()
        losses = Counter()
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

            result = CPOComparisonResult(
                comparison_poll,
                combination)
            wins[result.winner] += 1
            losses[result.looser] += 1

        assert wins.most_common()[0][0] not in losses, 'No-one won all their duels'
        return wins.most_common()[0][0]


    def resolve_tie(self, candidates, most_votes):
        # TODO Research and implement tiebreak methods
        # https://medium.com/freds-blog/explaining-cpo-stv-382444413292
        # https://medium.com/freds-blog/explaining-the-condorcet-system-9b4f47aa4e60
        return super(CPO_STV, self).resolve_tie(candidates, most_votes)

    def do_rounds(self):
        # type: (int) -> None

        self.select_multiple(
            filter(lambda c: c.votes > self.quota, self.candidates),
            ElectionRound.SELECTION_METHOD_DIRECT)

        self.select_multiple(
            self.get_best_approval(),
            ElectionRound.SELECTION_METHOD_CPO)
