## Now in __init__.py (modified version)

from decimal import Decimal
from random import choice
from typing import Iterable
from typing import List
from time import time
from copy import deepcopy


class Candidate:
    EXCLUDED = 0
    HOPEFUL = 1
    ELECTED = 2
    status = HOPEFUL
    votes = Decimal(0)

    def __init__(self, obj):
        # type: (object) -> None
        self.obj = obj

    def __str__(self):
        # type: () -> str
        return str(self.obj)

    @property
    def running(self):
        return self.status == self.HOPEFUL

    def __eq__(self, o):
        # type: (Candidate) -> bool
        return self.obj == o

    def __hash__(self):
        # type: () -> int
        return self.obj.__hash__()


class ElectionRound:
    SELECTION_METHOD_DIRECT = 0
    SELECTION_METHOD_HISTORY = 1
    SELECTION_METHOD_RANDOM = 2
    SELECTION_METHOD_NO_COMPETITION = 3
    SELECTION_METHODS = (
        'direct',
        'history',
        'dice roll',
        'no competition left',
    )
    selected = None
    status = None
    selection_method = None

    def __init__(self, vote_count, seats_left, _id):
        # type: (int, int, int) -> None
        self._id = _id

    def status_display(self):
        # type: () -> str
        return self.status == Candidate.ELECTED and 'Elected' or 'Excluded'

    def select(self, candidate, votes, method, status):
        # type: (Candidate, List[Candidate], int, int) -> None
        self.selected = candidate
        self.status = status
        self.votes = votes
        self.selection_method = method

    def __str__(self):
        # type: () -> str
        return 'Round {}: {} {}{}'.format(
            self._id,
            self.status_display(),
            self.selected,
            self.selection_method and ' ({})'.format(self.SELECTION_METHODS[self.selection_method]) or '')


class ElectionResult:
    exhausted = Decimal(0)
    runtime = .0

    def __init__(self, seats, vote_count):
        # type: (int, int) -> None
        self.rounds = []
        self.elected = []
        self.seats = seats
        self.vote_count = vote_count
        self.quota = Decimal((vote_count / (seats + 1)) + 1).quantize(Decimal(0))

    def __str__(self):
        # type: () -> str
        return '<ElectionResult in {} round(s): {}>'.format(len(self.rounds),  ', '.join(map(str, self.elected)))

    def new_round(self):
        self.rounds.append(ElectionRound(
            vote_count=self.vote_count-self.exhausted,
            seats_left=self.seats - len(self.elected),
            _id=len(self.rounds)+1))

    @property
    def current_round(self):
        # type: () -> ElectionRound
        return self.rounds[-1]

    def select(self, candidate, votes, method, status=Candidate.ELECTED):
        # type: (Candidate, List[Candidate], int, int) -> None
        candidate.status = status
        if status == Candidate.ELECTED:
            self.elected.append(candidate)
        self.current_round.select(candidate, votes, method, status)

    @property
    def complete(self):
        # type: () -> bool
        return len(self.elected) == self.seats


class ScottishSTVPoll:
    def __init__(self, seats, candidates):
        # type: (int, Iterable) -> None
        self.seats = seats
        self.candidates = map(Candidate, candidates)
        self.ballots = []
        self.errors = []

    def add_ballot(self, ballot):
        # type: (Iterable) -> None
        candidates = []
        for obj in ballot:
            try:
                candidates.append(self.get_candidate_for_object(obj))
            except KeyError:
                self.errors.append('Candidate "{}" not found'.format(obj))
        self.ballots.append(candidates)

    def get_candidate_for_object(self, obj):
        # type: (object) -> Candidate
        for candidate in self.candidates:
            if candidate.obj == obj:
                return candidate
        raise KeyError('Candidate not found')

    def transfer_votes(self, transfer_quota, candidate=None):
        # type: (Decimal, Candidate) -> Decimal
        transfer_quota = ScottishSTVPoll.round(transfer_quota)
        exhaustion = Decimal(0)
        if candidate:
#            print('Transfering votes for {} at {} quota.'.format(candidate, transfer_quota))
            for ballot in self.ballots:
                transfered = transfer_vote = False
                for bcandidate in ballot:
                    if not transfer_vote and bcandidate.running:
                        break
                    if bcandidate == candidate:
                        transfer_vote = True
                        continue
                    if transfer_vote and bcandidate.running:
                        bcandidate.votes += transfer_quota
                        transfered = True
                        break
                if transfer_vote and not transfered:
                    exhaustion += transfer_quota
        else:
            # print('Counting first hand votes')
            for ballot in self.ballots:
                for bcandidate in ballot:
                    if bcandidate.running:
                        bcandidate.votes += transfer_quota
                        break

        # print(', '.join([(str(v[0]) +' '+ str(v[1])) for v in votes.most_common()]))
        return exhaustion

    @property
    def still_running(self):
        # type: () -> List[Candidate]
        return list(filter(lambda c: c.running, self.candidates))

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

    def get_candidate(self, most_votes=True):
        # type: (bool) -> (Candidate, int)
        candidate = sorted(self.still_running, key=lambda c: c.votes, reverse=most_votes)[0]
        ties = [c for c in self.still_running if c.votes == candidate.votes]
        if len(ties) > 1:
            return self.resolve_tie(ties, most_votes)
        return candidate, ElectionRound.SELECTION_METHOD_DIRECT

    @staticmethod
    def round(value):
        # type: (Decimal) -> Decimal
        return value.quantize(Decimal('.00001'))

    @property
    def current_votes(self):
        # type: () -> List[Candidate]
        return deepcopy(self.still_running)

    @property
    def seats_to_fill(self):
        return self.seats - len(self.result.elected)

    def calculate(self):
        # type: () -> ElectionResult
        start_time = time()
        self.result = ElectionResult(self.seats, len(self.ballots))
        self.transfer_votes(transfer_quota=Decimal(1))
        while not self.result.complete:
            self.result.new_round()

            candidate, method = self.get_candidate()
            if candidate.votes >= self.result.quota:
                self.result.select(candidate, self.current_votes, method)
                tq = (candidate.votes - self.result.quota) / candidate.votes
                self.result.exhausted += self.transfer_votes(transfer_quota=tq, candidate=candidate)

            elif self.seats_to_fill == len(self.still_running):
                self.result.select(candidate, self.current_votes, ElectionRound.SELECTION_METHOD_NO_COMPETITION)

            else:
                candidate, method = self.get_candidate(most_votes=False)
                self.result.select(candidate, self.current_votes, method, Candidate.EXCLUDED)
                self.result.exhausted += self.transfer_votes(transfer_quota=Decimal(1), candidate=candidate)

        self.result.runtime = time() - start_time
        return self.result


def calculate_from_ballots(ballots, seats):
    # type: (Iterable[Iterable], int) -> ElectionResult
    candidates = set()
    for b in ballots:
        candidates.update(b)
    poll = ScottishSTVPoll(seats, candidates)
    for b in ballots:
        poll.add_ballot(b)
    return poll.calculate()

example_ballots = (
    (('orange',),)*4 +
    (('pear', 'orange',),)*2 +
    (('chocolate', 'strawberry',),)*8 +
    (('chocolate', 'bonbon',),)*4 +
    (('strawberry',),
     ('bonbon',))
)

if __name__ == '__main__':
    result = calculate_from_ballots(example_ballots, 3)
    print('\n{}\n'.format(result))
    for round in result.rounds:
        print(str(round))
    print('\nCalculated in {:.2f} seconds'.format(result.runtime))
