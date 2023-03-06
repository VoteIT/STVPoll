from decimal import Decimal
from typing import TypeVar, Protocol

Candidate = TypeVar("Candidate", int, str)
Candidates = tuple[Candidate, ...]
Votes = dict[Candidate, Decimal]
Rounds = tuple[Votes, ...]


class Quota(Protocol):
    """Calculate poll quota from valid ballot count and expected poll winners"""

    def __call__(self, ballot_count: int, winners: int) -> int:
        ...
