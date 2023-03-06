from decimal import Decimal
from random import sample
from typing import TypeVar

from stvpoll.abcs import ElectionRound

Candidate = TypeVar("Candidate", int, str)
Candidates = tuple[Candidate, ...]


class TiebreakRandom:
    method: int = ElectionRound.SELECTION_METHOD_RANDOM
    name = "random"
    used: bool
    shuffled: Candidates
    reversed: Candidates

    def __init__(self, candidates: Candidates):
        self.used = False
        self.shuffled = tuple(sample(candidates, len(candidates)))
        self.reversed = tuple(reversed(self.shuffled))

    def resolve(
        self,
        candidates: Candidates,
        history: tuple[dict[Candidate, Decimal], ...],
        lowest: bool = False,
    ) -> Candidate:
        self.used = True
        order = self.reversed if lowest else self.shuffled
        return next(c for c in order if c in candidates)

    def get_result_dict(self) -> dict:
        if not self.used:
            return {"randomized": False}
        return {
            "randomized": True,
            "random_order": self.shuffled,
        }


class TiebreakHistory:
    method: int = ElectionRound.SELECTION_METHOD_HISTORY
    name = "history"
    used: bool

    def __init__(self, candidates: Candidates):
        self.used = False

    def resolve(
        self,
        candidates: Candidates,
        history: tuple[dict[Candidate, Decimal], ...],
        lowest: bool = False,
    ) -> Candidate | None:
        for round in reversed(history):
            round_candidates: tuple[tuple[Candidate, Decimal], ...] = tuple(
                (c, v) for c, v in round.items() if c in candidates
            )
            minmax = min if lowest else max
            candidate, votes = minmax(round_candidates, key=lambda item: item[1])
            ties = tuple(c for c, v in round_candidates if v == votes)
            if len(ties) > 1:
                continue
            self.used = True
            return candidate

    def get_result_dict(self) -> dict:
        return {}
