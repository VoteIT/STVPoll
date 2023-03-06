from decimal import Decimal
from random import sample
from typing import Protocol, Type

from stvpoll.types import Candidates, Rounds, Candidate


class TiebreakStrategy(Protocol):
    method: int
    name: str

    def __init__(self, candidates: Candidates) -> None:
        ...

    def resolve(
        self, candidates: Candidates, history: Rounds, lowest: bool = False
    ) -> Candidates | Candidate:
        ...

    def get_result_dict(self) -> dict:
        ...


class TiebreakRandom:
    method: int = 2
    name = "random"
    used: bool = False
    shuffled: Candidates
    reversed: Candidates

    def __init__(self, candidates: Candidates):
        self.shuffled = tuple(sample(candidates, len(candidates)))
        self.reversed = tuple(reversed(self.shuffled))

    def resolve(
        self,
        candidates: Candidates,
        history: Rounds,
        lowest: bool = False,
    ) -> Candidate:
        self.used = True
        order = self.reversed if lowest else self.shuffled
        return next(c for c in order if c in candidates)

    def get_result_dict(self) -> dict:
        if self.used:
            return {
                "randomized": True,
                "random_order": self.shuffled,
            }
        return {}


class TiebreakHistory:
    method: int = 1
    name = "history"
    used: bool = False

    def __init__(self, candidates: Candidates):
        ...

    def resolve(
        self,
        candidates: Candidates,
        history: Rounds,
        lowest: bool = False,
    ) -> Candidates | Candidate:
        for round in reversed(history):
            round_candidates: tuple[tuple[Candidate, Decimal], ...] = tuple(
                (c, v) for c, v in round.items() if c in candidates
            )
            minmax = min if lowest else max
            candidate, votes = minmax(round_candidates, key=lambda item: item[1])
            candidates = tuple(c for c, v in round_candidates if v == votes)
            if len(candidates) == 1:
                return candidate
        return candidates

    def get_result_dict(self) -> dict:
        return {}
