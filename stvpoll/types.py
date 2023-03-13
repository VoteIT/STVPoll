from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import TypeVar, TypedDict

Candidate = TypeVar("Candidate", int, str)
Candidates = tuple[Candidate, ...]
Votes = dict[Candidate, Decimal]
VoteTransfers = dict[tuple[Candidate, Candidate], Decimal]
Rounds = tuple[Votes, ...]


class CandidateStatus(str, Enum):
    Elected = "Elected"
    Excluded = "Excluded"


class SelectionMethod(str, Enum):
    Direct = "Direct"
    TiebreakHistory = "Tiebreak (history)"
    TiebreakRandom = "Tiebreak (Random)"
    NoCompetition = "No competition left"
    CPO = "Comparison of Pairs of Outcomes"


class RoundDict(TypedDict):
    method: str
    selected: Candidates
    status: str
    vote_count: dict[Candidate, float]


class ResultDict(TypedDict):
    winners: Candidates
    candidates: Candidates
    complete: bool
    rounds: tuple[RoundDict, ...]
    randomized: bool
    quota: int
    runtime: float
    empty_ballot_count: int
