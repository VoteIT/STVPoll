from copy import deepcopy

from stvpoll import Candidate, ElectionRound
from stvpoll import STVPollBase
from stvpoll import hagenbach_bischof_quota


# class CPOExclusionPoll(STVPollBase):
#
#     def __init__(self, seats, candidates, quota=hagenbach_bischof_quota, winners=()):
#         super(CPOExclusionPoll, self).__init__(seats, candidates, quota)
#         self.non_excludes = winners
#         self.candidates = deepcopy(candidates)
#
#     def initial_votes(self):
#         pass
#
#     def calculate_round(self, quota):
#         if self.seats_to_fill == len(self.still_running):
#             self.select(self.still_running.pop(), ElectionRound.SELECTION_METHOD_NO_COMPETITION)
#
#         else:
#             candidate, method = self.get_candidate(most_votes=False, excludes=self.non_excludes)
#             self.select(candidate, method, Candidate.EXCLUDED)
#             self.transfer_votes(candidate)


class CPO_STV(STVPollBase):

    def __init__(self, seats, candidates, quota=hagenbach_bischof_quota, winners=()):
        super(CPO_STV, self).__init__(seats, candidates, quota)
        self.combinations = []
        self.winners = winners

    def calculate_combinations(self, quota):
        # type: (int) -> None
        from itertools import combinations
        for combination in combinations(self.still_running, self.seats_to_fill):
            poll = CPO_STV(
                seats=self.seats_to_fill,
                candidates=self.still_running,
                quota=lambda x: quota,
                winners=combination)

            for ballot in self.ballots:
                poll.add_ballot([b.obj for b in ballot])
            self.combinations.append(poll.calculate())

        for c in self.still_running:
            c.votes = max([e.votes for sublist in self.combinations for e in sublist.elected if e == c])

    def resolve_tie(self, candidates, most_votes):
        # TODO Research and implement tiebreak methods
        # https://medium.com/freds-blog/explaining-cpo-stv-382444413292
        # https://medium.com/freds-blog/explaining-the-condorcet-system-9b4f47aa4e60
        return super(CPO_STV, self).resolve_tie(candidates, most_votes)

    def calculate_round(self, quota):
        # type: (int) -> None
        candidate, method = self.get_candidate()

        # TODO Check, should this be done even i subcalculations?
        if not self.winners and candidate.votes >= quota:
            self.select(candidate, method)
            transfer_quota = (candidate.votes - quota) / candidate.votes
            self.transfer_votes(candidate, transfer_quota=transfer_quota)

        elif self.seats == 1:
            if len(self.still_running) == 1:
                self.select(self.still_running[0], ElectionRound.SELECTION_METHOD_CPO)
            else:
                candidate, method = self.get_candidate(most_votes=False, excludes=self.winners)
                self.select(candidate, method, status=Candidate.EXCLUDED)
                self.transfer_votes(candidate)

        else:
            if not self.combinations:
                self.calculate_combinations(quota)
                candidate, method = self.get_candidate()

            self.select(candidate, ElectionRound.SELECTION_METHOD_CPO)
