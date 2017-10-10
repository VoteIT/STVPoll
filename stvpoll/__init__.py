from collections import Counter
from copy import deepcopy
from decimal import Decimal
from math import floor
from random import choice
from time import time
from typing import Callable
from typing import Iterable
from typing import List

from stvpoll.exceptions import BallotException, STVException
from stvpoll.exceptions import CandidateDoesNotExist


def hagenbach_bischof_quota(poll):
    # type: (STVPollBase) -> int
    return int(floor(Decimal(poll.ballot_count) / (poll.seats + 1)))


def droop_quota(poll):
    # type: (STVPollBase) -> int
    return hagenbach_bischof_quota(poll) + 1


def hare_quota(poll):
    # type: (STVPollBase) -> int
    return int(floor(Decimal(poll.ballot_count) / poll.seats))


class Candidate:
    EXCLUDED = 0
    HOPEFUL = 1
    ELECTED = 2
    status = HOPEFUL
    votes = Decimal(0)

    def __init__(self, obj):
        # type: (object) -> None
        self.obj = obj

    def __repr__(self):
        # type: () -> str
        return '<Candidate: {}: {} votes>'.format(str(self.obj), self.votes)

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
    SELECTION_METHOD_CPO = 4
    SELECTION_METHODS = (
        'direct',
        'history',
        'dice roll',
        'no competition left',
        'Comparison of Pairs of Outcomes',
    )
    selected = None
    status = None
    selection_method = None

    def __init__(self, _id):
        # type: (int) -> None
        self._id = _id

    def status_display(self):
        # type: () -> str
        return self.status == Candidate.ELECTED and 'Elected' or 'Excluded'

    def select(self, candidate, votes, method, status):
        # type: (Candidate, List[Candidate], int, int) -> None
        self.selected = candidate
        self.status = status
        self.votes = deepcopy(votes)
        self.selection_method = method

    def __repr__(self):
        # type: () -> str
        return '<ElectionRound {}: {} {}{}>'.format(
            self._id,
            self.status_display(),
            self.selected,
            self.selection_method and ' ({})'.format(self.SELECTION_METHODS[self.selection_method]) or '')


class ElectionResult:
    exhausted = Decimal(0)
    runtime = .0
    _complete = False

    def __init__(self, poll):
        # type: (STVPollBase) -> None
        self.poll = poll
        self.rounds = []
        self.elected = []
        self.seats = poll.seats
        self.start_time = time()

    def __str__(self):
        # type: () -> str
        return '<ElectionResult in {} round(s): {}>'.format(len(self.rounds),  ', '.join(map(str, self.elected)))

    def new_round(self):
        self.rounds.append(ElectionRound(
            _id=len(self.rounds)+1))

    def finish(self):
        self._complete = True

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
        # print('Selected {} wth {} votes ({})'.format(candidate, candidate.votes, status))

    @property
    def complete(self):
        # type: () -> bool
        complete = len(self.elected) == self.seats
        if complete or self._complete:
            self.runtime = time() - self.start_time
            return True

    def elected_as_tuple(self):
        return tuple(map(lambda x: x.obj, self.elected))


class STVPollBase(object):
    _quota = None

    def __init__(self, seats, candidates, quota=droop_quota):
        # type: (int, List, Callable) -> None
        self.candidates = map(Candidate, candidates)
        self.ballots = Counter()
        self._quota_function = quota
        self.seats = seats
        self.errors = []
        if len(self.candidates) < self.seats:
            raise STVException('Not enough candidates to fill seats')

    def get_existing_candidate(self, obj):
        # type: (object) -> Candidate
        for candidate in self.candidates:
            if candidate.obj == obj:
                return candidate
        raise CandidateDoesNotExist()

    @property
    def quota(self):
        # type: () -> int
        if not self._quota:
            self._quota = self._quota_function(self)
        return self._quota

    @property
    def ballot_count(self):
        # type: () -> int
        return sum(self.ballots.values())

    def add_ballot(self, ballot, num=1):
        # type: (List, int) -> None
        candidates = []
        for obj in ballot:
            if isinstance(obj, Candidate):
                candidates.append(obj)
                continue
            try:
                candidates.append(self.get_existing_candidate(obj))
            except CandidateDoesNotExist:
                self.errors.append('Candidate "{}" not found'.format(obj))
        self.ballots[tuple(candidates)] += num

    def verify_ballot(self, ballot):
        # type: (List) -> None
        if len(set(ballot)) != len(ballot):
            raise BallotException("Duplicate candidates on ballot")
        for k in ballot:
            if k not in self.candidates:
                raise BallotException("%s is not in the list of candidates" % k)

    # TODO Remove excludes, probably
    def get_candidate(self, most_votes=True, excludes=None):
        # type: (bool) -> (Candidate, int, List[Candidate])
        if excludes:
            sample = filter(lambda c: c not in excludes, self.still_running)
            if not sample:
                raise CandidateDoesNotExist
        else:
            sample = self.still_running
        candidate = sorted(sample, key=lambda c: c.votes, reverse=most_votes)[0]
        ties = [c for c in sample if c.votes == candidate.votes]
        if len(ties) > 1:
            return self.resolve_tie(ties, most_votes)
        return candidate, ElectionRound.SELECTION_METHOD_DIRECT

    def resolve_tie(self, candidates, most_votes):
        # type: (List[Candidate], bool) -> (Candidate, int)
        for round in self.result.rounds[::-1]:  # TODO Make the code below readable
            round_votes = filter(lambda v: v in candidates, round.votes)
            sorted_round_votes = sorted(round_votes, key=lambda c: c.votes, reverse=most_votes)
            primary_candidate = sorted_round_votes[0]
            round_candidates = [v for v in round_votes if v.votes == primary_candidate.votes]

            if len(round_candidates) == 1:
                winner = [c for c in candidates if c == primary_candidate][0]
                return winner, ElectionRound.SELECTION_METHOD_HISTORY

            candidates = [c for c in candidates if c in round_candidates]

        return choice(candidates), ElectionRound.SELECTION_METHOD_RANDOM

    def transfer_votes(self, candidate, transfer_quota=Decimal(1)):
        # type: (Candidate, Decimal) -> None
        for ballot in self.ballots:
            ballot_quota = self.ballots[ballot] * transfer_quota
            if not ballot:
                self.result.exhausted += ballot_quota
                continue

            transfered = transfer_vote = False
            for bcandidate in ballot:
                if not transfer_vote and bcandidate.running:
                    break
                if bcandidate == candidate:
                    transfer_vote = True
                    continue
                if transfer_vote and bcandidate.running:
                    bcandidate.votes += ballot_quota
                    transfered = True
                    break
            if transfer_vote and not transfered:
                self.result.exhausted += ballot_quota


    def initial_votes(self):
        for ballot in self.ballots:
            try:
                ballot[0].votes += self.ballots[ballot]
            except IndexError:
                pass


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

    @property
    def complete(self):
        # type: () -> bool
        return self.result.complete

    def select(self, candidate, method, status=Candidate.ELECTED):
        # type: (Candidate, int, int) -> None
        self.result.new_round()
        self.result.select(candidate, self.still_running, method, status)

    def select_multiple(self, candidates, method, status=Candidate.ELECTED):
        # type: (Iterable[Candidate], int, int) -> None
        for candidate in sorted(candidates, key=lambda c: c.votes, reverse=True):
            self.select(candidate, method, status)

    def calculate(self):
        # type: () -> ElectionResult
        self.result = ElectionResult(self)
        self.initial_votes()
        self.do_rounds()
        return self.result

    def do_rounds(self):
        # type: () -> None
        while not self.result.complete:
            self.calculate_round()

    def calculate_round(self):
        # type: (int) -> None
        raise NotImplementedError()
