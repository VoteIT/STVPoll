from decimal import Decimal
from random import choice
from typing import List
from copy import deepcopy

from stvpoll import STVPollBase
from stvpoll import Candidate
from stvpoll import ElectionResult
from stvpoll import ElectionRound


class ScottishSTV(STVPollBase):
    def get_candidate(self, most_votes=True):
        # type: (bool) -> (Candidate, int)
        candidate = sorted(self.still_running, key=lambda c: c.votes, reverse=most_votes)[0]
        ties = [c for c in self.still_running if c.votes == candidate.votes]
        if len(ties) > 1:
            return self.resolve_tie(ties, most_votes)
        return candidate, ElectionRound.SELECTION_METHOD_DIRECT

    def transfer_votes(self, transfer_quota, candidate=None):
        # type: (Decimal, Candidate) -> Decimal
        transfer_quota = ScottishSTV.round(transfer_quota)
        exhaustion = Decimal(0)
        if candidate:
            # print('Transfering votes for {} at {} quota.'.format(candidate, transfer_quota))
            for ballot in self.ballots:
                transfered = transfer_vote = False
                for bcandidate in ballot:
                    if not transfer_vote and bcandidate.running:
                        break
                    if bcandidate == candidate:
                        transfer_vote = True
                        continue
                    if transfer_vote and bcandidate.running:
                        bcandidate.votes += self.ballots[ballot] * transfer_quota
                        transfered = True
                        break
                if transfer_vote and not transfered:
                    exhaustion += transfer_quota
        else:
            # print('Counting first hand votes')
            for ballot in self.ballots:
                for bcandidate in ballot:
                    if bcandidate.running:
                        bcandidate.votes += self.ballots[ballot] * transfer_quota
                        break

        return exhaustion

    def resolve_tie(self, candidates, most_votes):
        # type: (List[Candidate], bool) -> (Candidate, int)
        for round in self.result.rounds[:-1][::-1]:  # TODO Make the code below readable
            round_votes = filter(lambda v: v in candidates, round.votes)
            sorted_round_votes = sorted(round_votes, key=lambda c: c.votes, reverse=most_votes)
            primary_candidate = sorted_round_votes[0]
            round_candidates = [v for v in round_votes if v.votes == primary_candidate.votes]

            if len(round_candidates) == 1:
                winner = [c for c in candidates if c == primary_candidate][0]
                return winner, ElectionRound.SELECTION_METHOD_HISTORY

            candidates = [c for c in candidates if c in round_candidates]

        return choice(candidates), ElectionRound.SELECTION_METHOD_RANDOM

    @property
    def still_running(self):
        # type: () -> List[Candidate]
        return list(filter(lambda c: c.running, self.candidates))

    @property
    def current_votes(self):
        # type: () -> List[Candidate]
        return deepcopy(self.still_running)

    @property
    def seats_to_fill(self):
        # type () -> int
        return self.seats - len(self.result.elected)

    @staticmethod
    def round(value):
        # type: (Decimal) -> Decimal
        return value.quantize(Decimal('.00001'))

    def calculate(self):
        # type: () -> ElectionResult
        self.result = ElectionResult(self.seats, len(self.ballots))
        self.transfer_votes(transfer_quota=Decimal(1))
        quota = self.quota(self)
        while not self.result.complete:
            self.result.new_round()

            candidate, method = self.get_candidate()
            if candidate.votes >= quota:
                self.result.select(candidate, self.current_votes, method)
                tq = (candidate.votes - quota) / candidate.votes
                self.result.exhausted += self.transfer_votes(transfer_quota=tq, candidate=candidate)

            elif self.seats_to_fill == len(self.still_running):
                self.result.select(candidate, self.current_votes, ElectionRound.SELECTION_METHOD_NO_COMPETITION)

            else:
                candidate, method = self.get_candidate(most_votes=False)
                self.result.select(candidate, self.current_votes, method, Candidate.EXCLUDED)
                self.result.exhausted += self.transfer_votes(transfer_quota=Decimal(1), candidate=candidate)

        return self.result
