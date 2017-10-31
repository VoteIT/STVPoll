from __future__ import unicode_literals

from copy import deepcopy
from decimal import Decimal
from math import floor
from random import choice
from time import time
from typing import Callable
from typing import Iterable
from typing import List

from stvpoll.exceptions import BallotException, STVException, IncompleteResult
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


class PreferenceBallot(object):
    def __init__(self, preferences, count):
        # type: (List[Candidate],int) -> None
        self.preferences = preferences
        self.count = count
        self.multiplier = Decimal(1)

    @property
    def value(self):
        return self.multiplier * self.count

    def decrease_value(self, multiplier):
        self.multiplier *= multiplier

    @property
    def current_preference(self):
        try:
            return self.preferences[0]
        except IndexError:
            pass

    @property
    def exhausted(self):
        return len(self.preferences) == 0

    def get_transfer_preference(self, standing_candidates):
        while not self.exhausted:
            self.preferences.pop(0)
            if self.current_preference in standing_candidates:
                return self.current_preference


class Candidate(object):
    EXCLUDED = 0
    HOPEFUL = 1
    ELECTED = 2
    status = HOPEFUL
    votes = Decimal(0)

    def __init__(self, obj):
        # type: (object) -> None
        self.obj = obj

    def __repr__(self):
        # type: () -> basestring
        return '<Candidate: {}>'.format(str(self.obj))

    @property
    def running(self):
        return self.status == self.HOPEFUL

    def __eq__(self, o):
        # type: (Candidate) -> bool
        return self.obj == o

    def __hash__(self):
        # type: () -> int
        return self.obj.__hash__()


class ElectionRound(object):
    SELECTION_METHOD_DIRECT = 0
    SELECTION_METHOD_HISTORY = 1
    SELECTION_METHOD_RANDOM = 2
    SELECTION_METHOD_NO_COMPETITION = 3
    SELECTION_METHOD_CPO = 4
    SELECTION_METHODS = (
        'Direct',
        'Tiebreak (history)',
        'Tiebreak (Random)',
        'No competition left',
        'Comparison of Pairs of Outcomes',
    )
    status = None
    selection_method = None

    def __init__(self, _id):
        # type: (int) -> None
        self._id = _id
        self.selected = []

    def status_display(self):
        # type: () -> basestring
        return self.status == Candidate.ELECTED and 'Elected' or 'Excluded'

    def select(self, candidate, votes, method, status):
        # type: (Candidate, List[Candidate], int, int) -> None
        self.selected.append(candidate)
        self.status = status
        self.votes = deepcopy(votes)
        self.selection_method = method

    def __repr__(self):
        # type: () -> basestring
        return '<ElectionRound {}: {} {}{}>'.format(
            self._id,
            self.status_display(),
            ', '.join([c.obj for c in self.selected]),
            self.selection_method and ' ({})'.format(self.SELECTION_METHODS[self.selection_method]) or '')

    def as_dict(self):
        # type: () -> dict
        return {
            'status': self.status_display(),
            'selected': tuple(s.obj for s in self.selected),
            'method': self.SELECTION_METHODS[self.selection_method],
            'vote_count': tuple([{c.obj: c.votes} for c in self.votes]),
        }


class ElectionResult(object):
    exhausted = Decimal(0)
    runtime = .0
    randomized = False

    def __init__(self, poll):
        # type: (STVPollBase) -> None
        self.poll = poll
        self.rounds = []
        self.elected = []
        self.start_time = time()

    def __str__(self):
        # type: () -> basestring
        return '<ElectionResult in {} round(s): {}>'.format(len(self.rounds),  ', '.join(map(str, self.elected)))

    def new_round(self):
        self.rounds.append(ElectionRound(
            _id=len(self.rounds)+1))

    def finish(self):
        self.runtime = time() - self.start_time

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

    def select_multiple(self, candidates, votes, method, status=Candidate.ELECTED):
        # type: (Iterable[Candidate], List[Candidate], int, int) -> None
        for candidate in candidates:
            self.select(candidate, votes, method, status)

    @property
    def complete(self):
        # type: () -> bool
        return len(self.elected) == self.poll.seats

    def elected_as_tuple(self):
        # type: () -> tuple
        return tuple(map(lambda x: x.obj, self.elected))

    def elected_as_set(self):
        # type: () -> set
        return set(self.elected_as_tuple())

    def as_dict(self):
        # type: () -> dict
        return {
            'winners': self.elected_as_tuple(),
            'candidates': tuple([c.obj for c in self.poll.candidates]),
            'complete': self.complete,
            'rounds': tuple([r.as_dict() for r in self.rounds]),
            'randomized': self.randomized,
            'quota': self.poll.quota,
            'runtime': self.runtime,
        }


class STVPollBase(object):
    _quota = None

    def __init__(self, seats, candidates, quota=droop_quota, random_in_tiebreaks=True):
        # type: (int, List, Callable, bool) -> None
        self.candidates = map(Candidate, candidates)
        self.ballots = []
        self._quota_function = quota
        self.seats = seats
        self.errors = []
        self.random_in_tiebreaks = random_in_tiebreaks
        self.result = ElectionResult(self)
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
        return sum([b.count for b in self.ballots])

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
        self.ballots.append(PreferenceBallot(candidates, num))

    # def verify_ballot(self, ballot):
    #     # type: (List) -> None
    #     if len(set(ballot)) != len(ballot):
    #         raise BallotException("Duplicate candidates on ballot")
    #     for k in ballot:
    #         if k not in self.candidates:
    #             raise BallotException("%s is not in the list of candidates" % k)

    def get_candidate(self, most_votes=True):
        # type: (bool) -> (Candidate, int)
        candidate = sorted(self.standing_candidates, key=lambda c: c.votes, reverse=most_votes)[0]
        ties = [c for c in self.standing_candidates if c.votes == candidate.votes]
        if len(ties) > 1:
            return self.resolve_tie(ties, most_votes)
        return candidate, ElectionRound.SELECTION_METHOD_DIRECT

    def choice(self, candidates):
        if self.random_in_tiebreaks:
            self.result.randomized = True
            return choice(candidates)
        raise IncompleteResult('Unresolved tiebreak (random disallowed)')

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

        return self.choice(candidates), ElectionRound.SELECTION_METHOD_RANDOM

    def transfer_votes(self, candidate, transfer_quota=Decimal(1)):
        # type: (Candidate, Decimal) -> None
        for ballot in self.ballots:
            if candidate != ballot.current_preference:
                continue
            ballot.decrease_value(transfer_quota)
            target_candidate = ballot.get_transfer_preference(self.standing_candidates)
            if target_candidate:
                target_candidate.votes += ballot.value
            else:
                self.result.exhausted += ballot.value

            # transfered = transfer_vote = False
            # for bcandidate in ballot:
            #     if not transfer_vote and bcandidate.running:
            #         break
            #     if bcandidate == candidate:
            #         transfer_vote = True
            #         continue
            #     if transfer_vote and bcandidate.running:
            #         bcandidate.votes += ballot.value
            #         transfered = True
            #         break
            # if transfer_vote and not transfered:
            #     self.result.exhausted += ballot.value

    def initial_votes(self):
        for ballot in self.ballots:
            try:
                ballot.current_preference.votes += ballot.value
            except AttributeError:
                pass

    @property
    def standing_candidates(self):
        # type: () -> List[Candidate]
        return list(filter(lambda c: c.running, self.candidates))

    @property
    def still_running(self):
        # type: () -> List[Candidate]
        return self.standing_candidates

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
        self.result.new_round()
        self.result.select_multiple(candidates, self.still_running, method, status)

    def calculate(self):
        # type: () -> ElectionResult
        if not self.ballots:
            raise STVException('No ballots registered.')
        self.initial_votes()
        try:
            self.do_rounds()
        except IncompleteResult:
            pass
        self.result.finish()
        return self.result

    def do_rounds(self):
        # type: () -> None
        while self.seats_to_fill > 0:
            self.calculate_round()

    def calculate_round(self):
        # type: (int) -> None
        raise NotImplementedError()
