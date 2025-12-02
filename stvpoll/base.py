from contextlib import suppress
from decimal import Decimal
from itertools import groupby
from typing import Iterator

from more_itertools.recipes import partition

from stvpoll.abcs import PreferenceBallot
from stvpoll.exceptions import STVException, IncompleteResult
from stvpoll.quotas import Quota
from stvpoll.result import ElectionResult
from stvpoll.tiebreak_strategies import TiebreakStrategy
from stvpoll.transfer_strategies import TransferStrategy
from stvpoll.types import (
    BallotData,
    Candidate,
    Candidates,
    SelectionMethod,
    CandidateStatus,
    Votes,
)


def get_votes(
    ballots: tuple[PreferenceBallot, ...],
    candidates: Candidates,
    standing: set[Candidate],
) -> dict[Candidate, Decimal]:
    return {
        c: sum(
            (b.value for b in ballots if b.is_current_candidate(c, standing)),
            start=Decimal(0),
        )
        for c in candidates
        if c in standing
    }


def get_ballots(
    votes: BallotData, candidates: Candidates
) -> tuple[int, tuple[PreferenceBallot, ...]]:
    """
    Turn ballot data into PreferenceBallot tuple and also report empty ballots.
    :param votes: Can be a dict, Counter och iterable containing tuple of candidates and count
    :param candidates: Tuple of candidates, used to ensure no ballot contain missing candidates.
    :return: Empty count and ballots.
    >>> get_ballots({(): 3, (1,2): 2}, (1,2))
    (3, (PreferenceBallot([1,2], 2),))
    >>> get_ballots([([], 3), ([1,2], 2)], (1,2))
    (3, (PreferenceBallot([1,2], 2),))
    """
    if isinstance(votes, dict):
        ballots = tuple(
            PreferenceBallot(vote, count) for vote, count in votes.items() if vote
        )
        empty_ballots = votes[()]
    else:
        empty, votes = partition(lambda v: v[0], votes)
        empty_ballots = sum((count for _, count in empty), start=0)
        ballots = tuple(PreferenceBallot(tuple(vote), count) for vote, count in votes)
    for ballot in ballots:
        if missing := next((c not in candidates for c in ballot), None):
            raise STVException(f"Candidate {missing} not in candidates: {ballot}")
    return empty_ballots, ballots


def calculate_stv(
    candidates: Candidates,
    votes: BallotData,
    winners: int,
    *,
    pedantic_order: bool = False,
    tiebreak_strategies: tuple[TiebreakStrategy, ...] = (),
    transfer_strategy: TransferStrategy,
    quota_method: Quota,
) -> ElectionResult:
    """
    Base STV calculation method
    :param candidates: All candidates - ballots may not have other candidates
    :param votes: All ballots, with count for each ballot
    :param winners: Number of winners
    :param pedantic_order: Use tiebreaking mechanism for election order of candidates above quota
    :param tiebreak_strategies: Tiebreaking strategies
    :param transfer_strategy: Strategy to transfer votes
    :param quota_method: Method to calculate quota
    :return: Election result
    """
    if winners > len(candidates):
        raise STVException("Not enough candidates")
    result = ElectionResult(candidates=candidates, seats=winners)
    result.empty_ballot_count, ballots = get_ballots(votes, candidates)
    standing = set(candidates)
    quota = quota_method(sum((b.count for b in ballots), start=0), winners)

    def transfer_votes(
        transfers: Candidates, vote_count: Votes, decrease_value: bool = False
    ) -> Votes:
        log, exhausted, vote_count = transfer_strategy(
            ballots=ballots,
            quota=quota,
            decrease_value=decrease_value,
            transfers=transfers,
            vote_count=vote_count,
            standing=tuple(standing),
        )
        result.exhausted += exhausted
        result.transfer_log.append(log)
        return vote_count

    def resolve_tiebreak(tied: Candidates, lowest: bool = False) -> Candidate:
        """Go though tiebreaking methods in order, narrowing down to a single winner"""
        history = tuple(r.votes for r in result.rounds)
        for tiebreaker in tiebreak_strategies:
            tied = tiebreaker.resolve(tied, history, lowest=lowest)
            if not isinstance(tied, tuple):
                return tied
        raise IncompleteResult("Could not break tie")

    def iter_pedantic_order(
        tied: Candidates, current_votes: Votes
    ) -> Iterator[Candidate]:
        """
        Use tiebreaking mechanism to resolve order of tied candidates.
        Only for elected candidates.
        """
        for _, tied in groupby(tied, lambda c: current_votes[c]):
            tied = tuple(tied)
            while len(tied) > 1:
                nxt = resolve_tiebreak(tied)
                yield nxt
                tied = tuple(c for c in tied if c != nxt)
            yield from tied

    with suppress(IncompleteResult):
        while not result.complete:
            if len(standing) <= winners - len(result):
                last_standing = tuple(
                    sorted(standing, key=lambda c: votes[c], reverse=True)
                )
                result.select(last_standing, votes, SelectionMethod.NoCompetition)
                break

            votes = get_votes(ballots, candidates=candidates, standing=standing)
            if above_quota := tuple(
                sorted(
                    (c for c, vote_count in votes.items() if vote_count >= quota),
                    key=lambda c: votes[c],
                    reverse=True,
                )
            ):
                if pedantic_order:
                    above_quota = tuple(iter_pedantic_order(above_quota, votes))
                result.select(above_quota, votes, SelectionMethod.Direct)
                standing.difference_update(above_quota)
                votes = transfer_votes(
                    transfers=above_quota, vote_count=votes, decrease_value=True
                )

            else:
                min_votes = min(votes.values())
                exclude = tuple(
                    c for c, vote_count in votes.items() if vote_count == min_votes
                )
                if len(exclude) == 1:
                    exclude = exclude[0]
                else:
                    exclude = resolve_tiebreak(exclude, lowest=True)
                result.select(
                    exclude, votes, SelectionMethod.Direct, CandidateStatus.Excluded
                )
                standing.remove(exclude)
                votes = transfer_votes(transfers=(exclude,), vote_count=votes)

    return result.finalize(tiebreakers=tiebreak_strategies, quota=quota)
