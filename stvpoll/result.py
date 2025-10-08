from __future__ import annotations

from decimal import Decimal
from dataclasses import dataclass
from time import time

from typing import TYPE_CHECKING

from stvpoll.types import (
    CandidateStatus,
    SelectionMethod,
    Candidates,
    Votes,
    Candidate,
    ResultDict,
    RoundDict,
)

if TYPE_CHECKING:  # pragma: no coverage
    from .abcs import STVPollBase


@dataclass
class ElectionRound:
    status: CandidateStatus
    selection_method: SelectionMethod
    selected: Candidates
    votes: Votes

    def as_dict(self) -> RoundDict:
        return {
            "method": self.selection_method.value,
            "selected": self.selected,
            "status": self.status.value,
            "vote_count": {c: float(votes) for c, votes in self.votes.items()},
        }


class ElectionResult(list[Candidate]):
    exhausted = Decimal(0)
    runtime = 0.0
    rounds: list[ElectionRound]
    empty_ballot_count = 0
    # CPO STV requires manually setting randomized result
    _randomized = False

    def __init__(self, poll: STVPollBase) -> None:
        super().__init__()
        self.poll = poll
        self.rounds = []
        self.start_time = time()
        self.transfer_log = []

    def __repr__(self) -> str:  # pragma: no coverage
        return f'<ElectionResult in {len(self.rounds)} round(s): {", ".join(map(str, self))}>'

    @property
    def randomized(self):
        return self._randomized or any(
            r.selection_method == SelectionMethod.TiebreakRandom for r in self.rounds
        )

    def set_randomized(self):
        self._randomized = True

    def finish(self) -> None:
        self.runtime = round(time() - self.start_time, 6)

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

    def as_dict(self) -> ResultDict:
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
        for strategy in self.poll.tiebreakers:
            result.update(strategy.get_result_dict())
        return result
