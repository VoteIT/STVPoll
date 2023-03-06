from decimal import Decimal
from enum import Enum
from typing import TypeVar, Protocol

Candidate = TypeVar("Candidate", int, str)
Candidates = tuple[Candidate, ...]
Votes = dict[Candidate, Decimal]
Rounds = tuple[Votes, ...]


class Quota(Protocol):
    """Calculate poll quota from valid ballot count and expected poll winners"""

    def __call__(self, ballot_count: int, winners: int) -> int:
        ...


class CandidateStatus(str, Enum):
    Elected = "Elected"
    Excluded = "Excluded"


class SelectionMethod(str, Enum):
    Direct = "Direct"
    TiebreakHistory = "Tiebreak (history)"
    TiebreakRandom = "Tiebreak (Random)"
    NoCompetition = "No competition left"
    CPO = "Comparison of Pairs of Outcomes"
