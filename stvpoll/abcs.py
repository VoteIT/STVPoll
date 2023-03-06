from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from functools import cached_property
from time import time

from typing import Iterable, Callable, Iterator

from stvpoll.exceptions import (
    CandidateDoesNotExist,
    IncompleteResult,
    STVException,
)
from stvpoll.tiebreak_strategies import (
    TiebreakStrategy,
    TiebreakHistory,
    TiebreakRandom,
)
from stvpoll.types import (
    Quota,
    Candidates,
    Candidate,
    Votes,
    CandidateStatus,
    SelectionMethod,
)


class PreferenceBallot(list[Candidate]):
    def __init__(self, preferences: Candidates, count: int) -> None:
        super().__init__(preferences)
        self.count = count
        self.multiplier = Decimal(1)

    @property
    def value(self):
        return self.multiplier * self.count

    def decrease_value(self, multiplier: Decimal, round: Callable[[Decimal], Decimal]):
        self.multiplier = round(self.multiplier * multiplier)

    def get_next_preference(self, sample: Candidates) -> Candidate | None:
        return next((p for p in self if p in sample), None)

    def get_transfer_preference(self, standing_candidates: Candidates) -> Candidate:
        for candidate in self:
            if candidate in standing_candidates:
                return candidate


@dataclass
class ElectionRound:
    status: CandidateStatus
    selection_method: SelectionMethod
    selected: Candidates
    votes: Votes

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "selected": self.selected,
            "method": self.selection_method,
            "vote_count": tuple({c: votes} for c, votes in self.votes.items()),
        }


class ElectionResult(list[Candidate]):
    exhausted = Decimal(0)
    runtime = 0.0
    randomized = False
    rounds: list[ElectionRound]
    empty_ballot_count = 0

    def __init__(self, poll: STVPollBase) -> None:
        super().__init__()
        self.poll = poll
        self.rounds = []
        self.start_time = time()
        self.transfer_log = []

    def __repr__(self) -> str:  # pragma: no coverage
        return f'<ElectionResult in {len(self.rounds)} round(s): {", ".join(map(str, self))}>'

    def finish(self) -> None:
        self.runtime = time() - self.start_time

    # @property
    def select(
        self,
        candidates: Candidate | Candidates,
        votes: Votes,
        method: SelectionMethod,
        status: CandidateStatus = CandidateStatus.Elected,
    ):
        if not isinstance(candidates, tuple):
            candidates = (candidates,)
        self.rounds.append(
            ElectionRound(
                status=status,
                selection_method=method,
                selected=candidates,
                votes=votes,
            )
        )
        if status == CandidateStatus.Elected:
            self.extend(candidates)

    def still_standing(self, candidate: Candidate) -> bool:
        return all(candidate not in r.selected for r in self.rounds)

    @property
    def complete(self) -> bool:
        return len(self) == self.poll.seats

    def elected_as_tuple(self) -> tuple:
        return tuple(self)

    def elected_as_set(self) -> set:
        return set(self)

    def as_dict(self) -> dict:
        result = {
            "winners": self.elected_as_tuple(),
            "candidates": self.poll.candidates,
            "complete": self.complete,
            "rounds": tuple([r.as_dict() for r in self.rounds]),
            "randomized": self.randomized,
            "quota": self.poll.quota,
            "runtime": self.runtime,
            "empty_ballot_count": self.empty_ballot_count,
        }
        for strat in self.poll.tiebreakers:
            result.update(strat.get_result_dict())
        return result


class STVPollBase:
    ballots: list[PreferenceBallot]
    candidates: Candidates
    seats: int
    tiebreakers: list[TiebreakStrategy]
    current_votes: Votes

    def __init__(
        self,
        seats: int,
        candidates: Iterable[Candidate],
        quota: Quota | None = None,
        random_in_tiebreaks: bool = True,
        pedantic_order: bool = False,
    ):
        candidates = tuple(candidates)
        self.candidates = random.sample(candidates, len(candidates))
        self.ballots = []
        self._quota_function = quota
        self.seats = seats
        self.pedantic_order = pedantic_order
        self.result = ElectionResult(self)
        if len(self.candidates) < self.seats:
            raise STVException("Not enough candidates to fill seats")
        self.tiebreakers = [TiebreakHistory(tuple(candidates))]
        if random_in_tiebreaks:
            self.tiebreakers.append(TiebreakRandom(tuple(candidates)))

    @staticmethod
    def round(value: Decimal) -> Decimal:
        return round(value, 5).normalize()

    @cached_property
    def quota(self) -> int:
        return self._quota_function(self.ballot_count, self.seats)

    @property
    def ballot_count(self) -> int:
        return sum(b.count for b in self.ballots)

    def add_ballot(self, ballot: Candidates, num: int = 1):
        """Empty votes will not affect quota, but will be accounted for in result."""
        if set(ballot).difference(self.candidates):
            raise CandidateDoesNotExist
        if ballot:
            self.ballots.append(PreferenceBallot(ballot, num))
        else:
            self.result.empty_ballot_count += num

    def get_current_votes(self, candidate: Candidate) -> Decimal:
        return self.current_votes.get(candidate) or Decimal(0)

    def get_candidate(
        self, most_votes: bool = True, sample: Candidates | None = None
    ) -> tuple[Candidate, SelectionMethod]:
        if sample is None:
            sample = self.standing_candidates
        minmax = max if most_votes else min
        candidate = minmax(sample, key=lambda c: self.get_current_votes(c))
        ties = self.get_ties(candidate)
        if ties:
            return self.resolve_tie(ties, most_votes)
        return candidate, SelectionMethod.Direct

    def resolve_tie(
        self, tied: Candidates, most_votes: bool = True
    ) -> tuple[Candidate, int]:
        history = tuple(r.votes for r in self.result.rounds)
        for strategy in self.tiebreakers:
            resolved = strategy.resolve(tied, history, lowest=not most_votes)
            if resolved is None:
                continue
            if isinstance(resolved, tuple):
                tied = resolved
                continue
            return resolved, strategy.method
        raise IncompleteResult("Unresolved tiebreak (random disallowed)")

    def transfer_votes(
        self, _from: Candidate, transfer_quota: Decimal = Decimal(1)
    ) -> None:
        standing = self.standing_candidates
        transfers = Counter()
        for ballot in self.ballots:
            # Candidate is next in line among standing candidates
            if _from == ballot.get_next_preference(standing + (_from,)):
                ballot.decrease_value(transfer_quota, self.round)
                target_candidate = ballot.get_transfer_preference(standing)
                if target_candidate:
                    # target_candidate.votes += ballot.value
                    transfers[(_from, target_candidate)] += ballot.value
                else:
                    self.result.exhausted += ballot.value

        # Create a completely new current votes dictionary
        self.current_votes = {
            c: self.get_current_votes(c) + transfers[(_from, c)] for c in standing
        }

        self.result.transfer_log.append(
            {
                "transfers": transfers,
                "current_votes": self.current_votes,
                "exhausted_votes": self.result.exhausted,
            }
        )

    def initial_votes(self) -> None:
        standing = self.standing_candidates

        def get_initial_votes(candidate: Candidate):
            return sum(b.value for b in self.ballots if b[0] == candidate)

        self.current_votes = {c: get_initial_votes(c) for c in standing}
        self.result.transfer_log.append(
            {
                "transfers": None,
                "current_votes": self.current_votes,
                "exhausted_votes": self.result.exhausted,
            }
        )

    def get_ties(
        self, candidate: Candidate, sample: Candidates | None = None
    ) -> Candidates | None:
        if not sample:
            sample = self.standing_candidates
        votes = self.get_current_votes(candidate)
        ties = tuple(filter(lambda c: self.get_current_votes(c) == votes, sample))
        if len(ties) > 1:
            return ties

    @property
    def standing_candidates(self) -> Candidates:
        return tuple(filter(self.result.still_standing, self.candidates))

    @property
    def seats_to_fill(self) -> int:
        return self.seats - len(self.result)

    @property
    def complete(self) -> bool:
        return self.result.complete

    def select(
        self,
        candidate: Candidate,
        method: SelectionMethod,
        status: CandidateStatus = CandidateStatus.Elected,
    ) -> None:
        self.result.select(candidate, self.current_votes, method, status)

    def select_multiple(
        self,
        candidates: Candidates,
        method: SelectionMethod,
        status: CandidateStatus = CandidateStatus.Elected,
    ) -> None:
        if not candidates:
            return
        votes = self.current_votes
        elected = status == CandidateStatus.Elected
        if self.pedantic_order:
            # Select candidates in order, resolving ties.
            def get_pedantic_order(sample: Candidates) -> Iterator[Candidate]:
                while sample:
                    candidate, _ = self.get_candidate(most_votes=elected, sample=sample)
                    yield candidate
                    sample = tuple(filter(lambda c: c != candidate, candidates))

            candidates = tuple(get_pedantic_order(candidates))
        else:
            # Select candidates in order, not bothering with ties.
            candidates = tuple(
                sorted(
                    candidates, key=lambda c: self.get_current_votes(c), reverse=elected
                )
            )

        self.result.select(
            candidates,
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
