from __future__ import annotations

import random
from collections import Counter
from copy import deepcopy
from decimal import Decimal
from random import choice
from time import time

from typing import (
    Callable,
    Iterable,
    List,
    Union,
    Protocol,
)

from stvpoll.exceptions import (
    CandidateDoesNotExist,
    IncompleteResult,
    STVException,
)


def _minmax(iterable, key=None, high=True):
    if high:
        return max(iterable, key=key)
    return min(iterable, key=key)


class PreferenceBallot:
    def __init__(self, preferences: list[Candidate], count: int) -> None:
        self.preferences = preferences
        self.count = count
        self.multiplier = Decimal(1)

    @property
    def value(self):
        return self.multiplier * self.count

    def decrease_value(self, multiplier):
        self.multiplier *= multiplier

    @property
    def current_preference(self) -> Candidate | None:
        try:
            return self.preferences[0]
        except IndexError:
            pass

    @property
    def exhausted(self) -> bool:
        return len(self.preferences) == 0

    def get_transfer_preference(
        self, standing_candidates: list[Candidate]
    ) -> Candidate:
        while not self.exhausted:
            self.preferences.pop(0)
            if self.current_preference in standing_candidates:
                return self.current_preference


class Candidate:
    EXCLUDED = 0
    HOPEFUL = 1
    ELECTED = 2
    status = HOPEFUL
    votes = Decimal(0)
    votes_transferred = False

    def __init__(self, obj) -> None:
        self.obj = obj

    def __repr__(self) -> str:  # pragma: no coverage
        return f"<Candidate: {self.obj}>"

    @property
    def standing(self) -> bool:
        return self.status == self.HOPEFUL

    def __eq__(self, o: Candidate) -> bool:
        if isinstance(o, Candidate):
            return self.obj == o.obj
        return self.obj == o

    def __hash__(self) -> int:
        return self.obj.__hash__()


class ElectionRound:
    SELECTION_METHOD_DIRECT = 0
    SELECTION_METHOD_HISTORY = 1
    SELECTION_METHOD_RANDOM = 2
    SELECTION_METHOD_NO_COMPETITION = 3
    SELECTION_METHOD_CPO = 4
    SELECTION_METHODS = (
        "Direct",
        "Tiebreak (history)",
        "Tiebreak (Random)",
        "No competition left",
        "Comparison of Pairs of Outcomes",
    )
    status = None
    selection_method = None

    def __init__(self, _id: int) -> None:
        self._id = _id
        self.selected = []
        self.votes = []

    def status_display(self) -> str:
        return self.status == Candidate.ELECTED and "Elected" or "Excluded"

    def select(
        self,
        candidate: Candidate | list[Candidate],
        votes: list[Candidate],
        method: int,
        status: int,
    ):
        if isinstance(candidate, list):
            self.selected += candidate
        else:
            self.selected.append(candidate)
        self.status = status
        self.votes = deepcopy(votes)
        self.selection_method = method

    @property
    def method_str(self) -> str:
        if isinstance(self.selection_method, int):
            return self.SELECTION_METHODS[self.selection_method]

    def __repr__(self) -> str:  # pragma: no coverage
        return "<ElectionRound {}: {} {}{}>".format(
            self._id,
            self.status_display(),
            ", ".join([c.obj for c in self.selected]),
            self.selection_method and " ({})".format(self.method_str),
        )

    def as_dict(self) -> dict:
        return {
            "status": self.status_display(),
            "selected": tuple(s.obj for s in self.selected),
            "method": self.method_str,
            "vote_count": tuple({c.obj: c.votes} for c in self.votes),
        }


class ElectionResult:
    exhausted = Decimal(0)
    runtime = 0.0
    randomized = False
    empty_ballot_count = 0

    def __init__(self, poll: STVPollBase) -> None:
        self.poll = poll
        self.rounds = []
        self.elected = []
        self.start_time = time()
        self.transfer_log = []

    def __repr__(self) -> str:  # pragma: no coverage
        return f'<ElectionResult in {len(self.rounds)} round(s): {", ".join(map(str, self.elected))}>'

    def new_round(self):
        self.rounds.append(ElectionRound(_id=len(self.rounds) + 1))

    def finish(self) -> None:
        self.runtime = time() - self.start_time

    @property
    def current_round(self) -> ElectionRound:
        return self.rounds[-1]

    def _set_candidate_status(self, candidate: Candidate, status: int) -> None:
        candidate.status = status
        if status == Candidate.ELECTED:
            self.elected.append(candidate)

    def select(
        self,
        candidate: Candidate | list[Candidate],
        votes: list[Candidate],
        method: int,
        status: int = Candidate.ELECTED,
    ):
        if isinstance(candidate, list):
            for c in candidate:
                self._set_candidate_status(c, status)
        else:
            self._set_candidate_status(candidate, status)
        self.current_round.select(candidate, votes, method, status)

    @property
    def complete(self) -> bool:
        return len(self.elected) == self.poll.seats

    def elected_as_tuple(self) -> tuple:
        return tuple(map(lambda x: x.obj, self.elected))

    def elected_as_set(self) -> set:
        return set(self.elected_as_tuple())

    def as_dict(self) -> dict:
        return {
            "winners": self.elected_as_tuple(),
            "candidates": tuple([c.obj for c in self.poll.candidates]),
            "complete": self.complete,
            "rounds": tuple([r.as_dict() for r in self.rounds]),
            "randomized": self.randomized,
            "quota": self.poll.quota,
            "runtime": self.runtime,
            "empty_ballot_count": self.empty_ballot_count,
        }


class Quota(Protocol):
    def __call__(self, poll: STVPollBase) -> int:
        ...


class STVPollBase:
    _quota: int | None = None

    def __init__(
        self,
        seats: int,
        candidates: Iterable,
        quota: Quota | None = None,
        random_in_tiebreaks: bool = True,
        pedantic_order: bool = False,
    ):
        self.candidates = [Candidate(c) for c in candidates]
        random.shuffle(self.candidates)
        self.ballots = []
        self._quota_function = quota
        self.seats = seats
        self.errors = []
        self.random_in_tiebreaks = random_in_tiebreaks
        self.pedantic_order = pedantic_order
        self.result = ElectionResult(self)
        if len(self.candidates) < self.seats:
            raise STVException("Not enough candidates to fill seats")

    def get_existing_candidate(self, obj) -> Candidate:
        for candidate in self.candidates:
            if candidate == obj:
                return candidate
        raise CandidateDoesNotExist

    @property
    def quota(self) -> int:
        if not self._quota:
            self._quota = self._quota_function(self)
        return self._quota

    @property
    def ballot_count(self) -> int:
        return sum([b.count for b in self.ballots])

    def add_ballot(self, ballot: list, num: int = 1):
        candidates = []
        for obj in ballot:
            candidates.append(self.get_existing_candidate(obj))

        # Empty votes will not affect quota, but will be accounted for in result.
        if candidates:
            self.ballots.append(PreferenceBallot(candidates, num))
        else:
            self.result.empty_ballot_count += num

    def get_candidate(
        self, most_votes: bool = True, sample: list[Candidate] | None = None
    ) -> tuple[Candidate, int]:
        if sample is None:
            sample = self.standing_candidates
        candidate = _minmax(sample, key=lambda c: c.votes, high=most_votes)
        ties = self.get_ties(candidate)
        if ties:
            return self.resolve_tie(ties, most_votes)
        return candidate, ElectionRound.SELECTION_METHOD_DIRECT

    def choice(self, candidates):
        if self.random_in_tiebreaks:
            self.result.randomized = True
            return choice(candidates)
        raise IncompleteResult("Unresolved tiebreak (random disallowed)")

    def resolve_tie(
        self, candidates: list[Candidate], most_votes: bool = True
    ) -> tuple[Candidate, int]:
        for stage in self.result.transfer_log[::-1]:
            stage_votes = [v for v in stage["current_votes"] if v in candidates]
            primary_candidate = _minmax(
                stage_votes, key=lambda c: c.votes, high=most_votes
            )
            ties = self.get_ties(primary_candidate, stage_votes)
            if ties:
                candidates = [c for c in candidates if c in ties]
            else:
                winner = candidates[
                    candidates.index(primary_candidate)
                ]  # Get correct Candidate instance
                return winner, ElectionRound.SELECTION_METHOD_HISTORY
        return self.choice(candidates), ElectionRound.SELECTION_METHOD_RANDOM

    def transfer_votes(
        self, candidate: Candidate, transfer_quota: Decimal = Decimal(1)
    ) -> None:
        transfers = Counter()
        for ballot in self.ballots:
            if candidate == ballot.current_preference:
                ballot.decrease_value(transfer_quota)
                target_candidate = ballot.get_transfer_preference(
                    self.standing_candidates
                )
                if target_candidate:
                    target_candidate.votes += ballot.value
                    transfers[(candidate, target_candidate)] += ballot.value
                else:
                    self.result.exhausted += ballot.value

        self.result.transfer_log.append(
            {
                "transfers": transfers,
                "current_votes": self.current_votes,
                "exhausted_votes": self.result.exhausted,
            }
        )
        candidate.votes_transferred = True

    def initial_votes(self) -> None:
        for ballot in self.ballots:
            assert ballot.current_preference, "Initial votes called with an empty vote"
            ballot.current_preference.votes += ballot.value

        self.result.transfer_log.append(
            {
                "transfers": None,
                "current_votes": self.current_votes,
                "exhausted_votes": self.result.exhausted,
            }
        )

    def get_ties(
        self, candidate: Candidate, sample: list[Candidate] | None = None
    ) -> list[Candidate]:
        if not sample:
            sample = self.standing_candidates
        ties = [c for c in sample if c.votes == candidate.votes]
        if len(ties) > 1:
            return ties

    @property
    def standing_candidates(self) -> list[Candidate]:
        return [c for c in self.candidates if c.standing]

    @property
    def current_votes(self) -> list[Candidate]:
        return deepcopy(self.standing_candidates)

    @property
    def seats_to_fill(self) -> int:
        return self.seats - len(self.result.elected)

    @property
    def complete(self) -> bool:
        return self.result.complete

    def select(
        self, candidate: Candidate, method: int, status: int = Candidate.ELECTED
    ) -> None:
        self.result.new_round()
        self.result.select(candidate, self.current_votes, method, status)

    def select_multiple(
        self, candidates: list[Candidate], method: int, status: int = Candidate.ELECTED
    ) -> None:
        if candidates:
            self.result.new_round()
            votes = self.current_votes  # Copy vote data before multiple selection
            if self.pedantic_order:
                # Select candidates in order, resolving ties.
                while candidates:
                    candidate, method = self.get_candidate(
                        most_votes=status == Candidate.ELECTED, sample=candidates
                    )
                    index = candidates.index(candidate)

                    self.result.select(candidates.pop(index), votes, method, status)
            else:
                # Select candidates in order, not bothering with ties.
                self.result.select(
                    sorted(candidates, key=lambda c: c.votes, reverse=True),
                    votes,
                    method,
                    status,
                )

    def calculate(self) -> ElectionResult:
        # if not self.ballots:  # pragma: no coverage
        #     raise STVException('No ballots registered.')
        self.initial_votes()
        try:
            self.do_rounds()
        except IncompleteResult:
            pass
        self.result.finish()
        return self.result

    def do_rounds(self) -> None:
        while self.seats_to_fill:
            self.calculate_round()

    def calculate_round(self) -> None:  # pragma: no coverage
        raise NotImplementedError()
