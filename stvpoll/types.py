from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from enum import Enum
from typing import TypeVar, TypedDict

from typing_extensions import Counter

Candidate = TypeVar("Candidate", int, str)
Candidates = tuple[Candidate, ...]
BallotData = dict[Candidates, int] | Iterable[tuple[Iterable[Candidate], int]]
Votes = dict[Candidate, Decimal]
VoteTransfers = Counter[tuple[Candidate, Candidate]]
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


class TransfersDict(TypedDict):
    transfers: VoteTransfers
    current_votes: Votes
    exhausted_votes: Decimal


class ResultDict(TypedDict):
    winners: Candidates
    candidates: Candidates
    complete: bool
    rounds: tuple[RoundDict, ...]
    randomized: bool
    quota: int
    runtime: float
    empty_ballot_count: int
