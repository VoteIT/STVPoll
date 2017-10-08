from copy import deepcopy

from decimal import Decimal
from stvpoll import Candidate, ElectionRound, ElectionResult, CandidateDoesNotExist
from stvpoll import STVPollBase
from stvpoll import hagenbach_bischof_quota
from typing import Iterable
from typing import List


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
    def __init__(self, poll, compared, candidates):
        # type: (CPOComparisonPoll, set[Candidate], List[Candidate]) -> None
        self.candidates = candidates
        self.others = set(compared).difference(candidates)
        self.poll = poll

    def __cmp__(self, other):
        # type: (CPOComparisonResult) -> bool
        return self.total > other.total

    @property
    def total(self):
        # type: () -> Decimal
        return self.poll.total_except(list(self.others))

    def update_votes(self):
        for candidate in self.candidates:
            candidate.votes = [c for c in self.poll.candidates if c == candidate][0].votes


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

            this_runner = []
            for candidates in combination:
                this_runner.append(CPOComparisonResult(
                    comparison_poll,
                    compared,
                    candidates))

            if leader:
                if max(this_runner) > max(leader):
                    leader = this_runner
            else:
                leader = this_runner

        winning_combination = max(leader)
        winning_combination.update_votes()
        return winning_combination.candidates


    def resolve_tie(self, candidates, most_votes):
        # TODO Research and implement tiebreak methods
        # https://medium.com/freds-blog/explaining-cpo-stv-382444413292
        # https://medium.com/freds-blog/explaining-the-condorcet-system-9b4f47aa4e60
        return super(CPO_STV, self).resolve_tie(candidates, most_votes)

    def do_rounds(self):
        # type: (int) -> None

        self.select_multiple(
            filter(lambda c: c.votes >= self.quota, self.candidates),
            ElectionRound.SELECTION_METHOD_DIRECT)

        self.select_multiple(
            self.get_best_approval(),
            ElectionRound.SELECTION_METHOD_CPO)
