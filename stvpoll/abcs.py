from __future__ import annotations

import random
from decimal import Decimal
from functools import cached_property

from typing import Iterable, Callable, Iterator

from .exceptions import (
    CandidateDoesNotExist,
    IncompleteResult,
    STVException,
)
from .result import ElectionResult
from .tiebreak_strategies import (
    TiebreakStrategy,
    TiebreakHistory,
    TiebreakRandom,
)
from .transfer_strategies import (
    TransferStrategy,
    transfer_serial,
)
from .types import (
    Candidates,
    Candidate,
    Votes,
    CandidateStatus,
    SelectionMethod,
)
from .quotas import Quota


def rounding_method(value: Decimal) -> Decimal:
    return round(value, 5).normalize()


class PreferenceBallot(list[Candidate]):
    def __init__(
        self,
        preferences: Candidates,
        count: int,
        rounding: Callable[[Decimal], Decimal] = rounding_method,
    ) -> None:
        super().__init__(preferences)
        self.count = count
        self.multiplier = Decimal(1)
        self.round = rounding

    @property
    def value(self) -> Decimal:
        return self.multiplier * self.count

    def decrease_value(self, multiplier: Decimal) -> None:
        self.multiplier = self.round(self.multiplier * multiplier)

    def get_next_preference(self, sample: Candidates) -> Candidate | None:
        return next((p for p in self if p in sample), None)


class STVPollBase:
    ballots: list[PreferenceBallot]
    candidates: Candidates
    seats: int
    tiebreakers: list[TiebreakStrategy]
    current_votes: Votes
    multiple_winners: bool = True
    # Default methods
    round = staticmethod(rounding_method)
    transfer_strategy: TransferStrategy = staticmethod(transfer_serial)

    def __init__(
        self,
        seats: int,
        candidates: Iterable[Candidate],
        quota: Quota | None = None,
        random_in_tiebreaks: bool = True,
        pedantic_order: bool = False,
    ):
        candidates = tuple(candidates)
        self.candidates = tuple(random.sample(candidates, len(candidates)))
        self.ballots = []
        self._quota_function = quota
        self.seats = seats
        self.pedantic_order = pedantic_order
        self.result = ElectionResult(self)
        if len(self.candidates) < self.seats:
            raise STVException("Not enough candidates to fill seats")
        self.tiebreakers = [TiebreakHistory()]
        if random_in_tiebreaks:
            self.tiebreakers.append(TiebreakRandom(candidates))

    @cached_property
    def quota(self) -> int:
        return self._quota_function(self.ballot_count, self.seats)

    @property
    def ballot_count(self) -> int:
        return sum(b.count for b in self.ballots)

    def add_ballot(self, ballot: Iterable[Candidate], num: int = 1):
        """Empty votes will not affect quota, but will be accounted for in result."""
        ballot = tuple(ballot)
        if set(ballot).difference(self.candidates):
            raise CandidateDoesNotExist
        if ballot:
            self.ballots.append(PreferenceBallot(ballot, num, self.round))
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
        ties = self.get_ties(candidate, sample)
        if ties:
            return self.resolve_tie(ties, most_votes)
        return candidate, SelectionMethod.Direct

    def resolve_tie(
        self, tied: Candidates, most_votes: bool = True
    ) -> tuple[Candidate, SelectionMethod]:
        history = tuple(r.votes for r in self.result.rounds)
        for strategy in self.tiebreakers:
            resolved = strategy.resolve(tied, history, lowest=not most_votes)
            if isinstance(resolved, tuple):
                tied = resolved
                continue
            return resolved, strategy.method
        raise IncompleteResult("Unresolved tiebreak (random disallowed)")

    def transfer_votes(
        self, candidates: Candidates | Candidate, decrease_value: bool = False
    ) -> None:
        """
        Use Transfer Strategy to transfer votes for elected or excluded candidates.
        Set decrease_value = True if elected.
        """
        if not isinstance(candidates, tuple):
            candidates = (candidates,)

        transfers, exhausted, self.current_votes = self.transfer_strategy(
            ballots=self.ballots,
            vote_count=self.current_votes,
            transfers=candidates,
            standing=self.standing_candidates,
            quota=self.quota,
            decrease_value=decrease_value,
        )
        self.result.exhausted += exhausted

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

    def get_ties(self, candidate: Candidate, sample: Candidates) -> Candidates | None:
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

    def _get_sorted_elect_order(self, candidates: Candidates) -> Candidates:
        """Select candidates in order, not bothering with ties."""
        return tuple(
            sorted(candidates, key=lambda c: self.get_current_votes(c), reverse=True)
        )

    def _get_pendantic_elect_order(self, candidates: Candidates) -> Iterator[Candidate]:
        """Generate list of candidates in order, resolving ties."""
        while candidates:
            candidate, _ = self.get_candidate(sample=candidates)
            yield candidate
            candidates = tuple(filter(lambda c: c != candidate, candidates))

    def elect(
        self, candidates: Candidates | Candidate, method: SelectionMethod
    ) -> Candidates:
        """Elect single or list of candidates, returning election order."""
        # Calling with empty list of candidates is OK
        if not candidates:
            return ()
        # Ensure tuple
        if not isinstance(candidates, tuple):
            candidates = (candidates,)
        # If multiple, get correct order
        if len(candidates) > 1:
            candidates = (
                tuple(self._get_pendantic_elect_order(candidates))
                if self.pedantic_order
                else self._get_sorted_elect_order(candidates)
            )
        self.result.select(
            candidates, self.current_votes, method, CandidateStatus.Elected
        )
        return candidates

    def exclude(self, candidate: Candidate, method: SelectionMethod) -> None:
        self.result.select(
            candidate, self.current_votes, method, CandidateStatus.Excluded
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
