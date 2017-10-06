from copy import deepcopy
from decimal import Decimal

from stvpoll import ElectionResult, Candidate, ElectionRound
from stvpoll import STVPollBase
from stvpoll import hagenbach_bischof_quota


class CPOExclusionPoll(STVPollBase):

    def __init__(self, seats=0, candidates=(), quota=hagenbach_bischof_quota, non_excludes=None):
        self.non_excludes = non_excludes
        super(CPOExclusionPoll, self).__init__(seats, candidates, quota)

    def calculate_round(self, quota):
        if self.seats_to_fill == len(self.still_running):
            self.select(self.still_running.pop(), ElectionRound.SELECTION_METHOD_NO_COMPETITION)

        else:
            candidate, method = self.get_candidate(most_votes=False, excludes=self.non_excludes)
            self.select(candidate, method, Candidate.EXCLUDED)
            self.result.exhausted += self.transfer_votes(candidate=candidate)


class CPO_STV(STVPollBase):

    def __init__(self, seats=0, candidates=(), quota=hagenbach_bischof_quota):
        super(CPO_STV, self).__init__(seats, candidates, quota)
        self.cpo_matrix = []

    def strip_candidates(self, candidates):
        # type: (List[Candidate]) -> List(object)
        return [c.obj for c in candidates]

    def make_matrix(self):
        # type: () -> None
        from itertools import combinations
        for combination in combinations(self.still_running, self.seats_to_fill):
            poll = CPOExclusionPoll(
                seats=self.seats_to_fill,
                candidates=self.strip_candidates(self.still_running),
                non_excludes=self.strip_candidates(combination))

            for ballot in self.ballots:
                poll.add_ballot([b.obj for b in ballot])
            self.cpo_matrix.append(poll.calculate())

    def calculate_round(self, quota):
        # type: () -> ElectionResult
        candidate, method = self.get_candidate()
        if candidate.votes >= quota:
            self.select(candidate, method)
        else:
            if not self.cpo_matrix:
                self.make_matrix()

                for result in self.cpo_matrix:
                    for that_candidate in result.elected:
                        this_candidate = self.get_existing_candidate(that_candidate.obj)
                        if that_candidate.votes > this_candidate.votes:
                            this_candidate.votes = that_candidate.votes
                candidate, method = self.get_candidate()

            self.select(candidate, ElectionRound.SELECTION_METHOD_CPO)
