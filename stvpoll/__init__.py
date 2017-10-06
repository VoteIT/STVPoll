from collections import Counter
from decimal import Decimal

from math import floor
from time import time

from typing import Callable
from typing import List


class BallotException(Exception):
    pass
class CandidateDoesNotExist(BallotException):
    pass

def droop_quota(poll):
    # type: (STVPollBase) -> int
    return int(floor((Decimal(poll.ballot_count) / (poll.seats +1 )) + 1))

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
        self.start_time = time()

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
        complete = len(self.elected) == self.seats
        if complete:
            self.runtime = time() - self.start_time
        return complete

    def elected_as_tuple(self):
        return tuple(map(lambda x: x.obj, self.elected))


class STVPollBase(object):
    quota = None
    candidates = ()
    seats = 0

    def __init__(self, seats=0, candidates=(), quota=droop_quota):
        # type: (int, List, Callable) -> None
        self.candidates = map(Candidate, candidates)
        self.ballots = Counter()
        self.quota = quota
        self.seats = seats
        self.errors = []

    def get_existing_candidate(self, obj):
        # type: (object) -> Candidate
        for candidate in self.candidates:
            if candidate.obj == obj:
                return candidate
        raise CandidateDoesNotExist()

    @property
    def ballot_count(self):
        # type: () -> int
        return sum(self.ballots.values())

    def add_ballot(self, ballot, num=1):
        # type: (List, int) -> None
        candidates = []
        for obj in ballot:
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

    def calculate(self):
        raise NotImplementedError()
