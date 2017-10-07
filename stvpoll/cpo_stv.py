from copy import deepcopy

from decimal import Decimal
from stvpoll import Candidate, ElectionRound, ElectionResult, CandidateDoesNotExist
from stvpoll import STVPollBase
from stvpoll import hagenbach_bischof_quota
from typing import List


class CPOComparisonPoll(STVPollBase):

    def __init__(self, seats, candidates, quota=hagenbach_bischof_quota, winners=(), compared=()):
        super(CPOComparisonPoll, self).__init__(seats, candidates, quota)
        self.result = ElectionResult(self)
        self.winners = [self.get_existing_candidate(c.obj) for c in winners]
        self.compared = [self.get_existing_candidate(c.obj) for c in compared]
        self.below_quota = False

    def transfer_votes(self, candidate, transfer_quota=Decimal(1)):
        super(CPOComparisonPoll, self).transfer_votes(candidate, transfer_quota)
        quota = self.quota(self)
        if candidate.votes > quota:
            candidate.votes = quota

    def select_round(self, candidate, quota, status=Candidate.ELECTED):
        # type: (Candidate, int, int) -> None
        candidate = [c for c in self.candidates if c == candidate][0]
        self.select(candidate, ElectionRound.SELECTION_METHOD_CPO, status)
        transfer_quota = status == Candidate.ELECTED and (candidate.votes - quota) / candidate.votes or 1
        self.transfer_votes(candidate, transfer_quota=transfer_quota)

    def calculate_round(self, quota):
        # type: (int) -> None
        exclude = set(self.still_running).difference(self.winners)
        if exclude:
            self.select_round(exclude.pop(), quota, Candidate.EXCLUDED)
        else:
            try:
                candidate, method = self.get_candidate(excludes=self.compared)
            except CandidateDoesNotExist:
                self.result.finish()
            else:
                if candidate.votes >= quota:
                    self.select_round(candidate, quota)
                else:
                    self.result.finish()

    @property
    def not_excluded(self):
        # type: () -> List[Candidate]
        return list(filter(lambda c: c.status != Candidate.EXCLUDED, self.candidates))

    def total_except(self, candidates):
        # type: (List[Candidate]) -> Decimal
        return sum([c.votes for c in self.not_excluded if c not in candidates])


class CPOComparisonResult:
    def __init__(self, poll, compared, candidate):
        # type: (CPOComparisonPoll, set, Candidate) -> None
        self.candidate = candidate
        self.others = set(compared)
        self.others.discard(candidate)
        self.poll = poll

    def __cmp__(self, other):
        # type: (CPOComparisonResult) -> bool
        return self.total > other.total

    @property
    def total(self):
        return self.poll.total_except(list(self.others))


class CPO_STV(STVPollBase):

    def __init__(self, seats, candidates, quota=hagenbach_bischof_quota):
        super(CPO_STV, self).__init__(seats, candidates, quota)

    def get_best_approval(self):
        # type: (int) -> Candidate
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
                [c.obj for c in self.candidates],
                winners=winners,
                compared=compared)

            for ballot in self.ballots:
                comparison_poll.add_ballot([c.obj for c in ballot], self.ballots[ballot])
            comparison_poll.calculate()

            this_runner = []
            for candidate in compared:
                this_runner.append(CPOComparisonResult(
                    comparison_poll,
                    compared,
                    candidate))

            if leader:
                if max(this_runner) > max(leader):
                    leader = this_runner
            else:
                leader = this_runner

        winner = max(leader)
        winner.candidate.votes = [c for c in winner.poll.candidates if c == winner.candidate][0].votes
        return winner.candidate


    def resolve_tie(self, candidates, most_votes):
        # TODO Research and implement tiebreak methods
        # https://medium.com/freds-blog/explaining-cpo-stv-382444413292
        # https://medium.com/freds-blog/explaining-the-condorcet-system-9b4f47aa4e60
        return super(CPO_STV, self).resolve_tie(candidates, most_votes)

    def calculate_round(self, quota):
        # type: (int) -> None
        candidate, method = self.get_candidate()

        if candidate.votes >= quota or len(self.still_running) == self.seats_to_fill:
            self.select(candidate, method)

        # elif len(self.still_running) <= 2:
        #     candidate, method = self.get_candidate(most_votes=False)
        #     self.select(candidate, method, Candidate.EXCLUDED)

        else:
            self.select(self.get_best_approval(), ElectionRound.SELECTION_METHOD_CPO)
