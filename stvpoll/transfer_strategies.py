from __future__ import annotations

from decimal import Decimal
from typing import Iterator, TYPE_CHECKING, Counter, Protocol

from stvpoll.types import Candidates, Candidate, Votes, VoteTransfers

if TYPE_CHECKING:  # pragma: no coverage
    from stvpoll.abcs import PreferenceBallot


class TransferStrategy(Protocol):
    """Transfer votes, returning vote transfer mapping, exhausted votes and resulting Votes"""

    def __call__(
        self,
        *,
        ballots: list[PreferenceBallot],
        vote_count: Votes,
        transfers: Candidates,
        standing: Candidates,
        quota: int,
        decrease_value: bool,
    ) -> tuple[VoteTransfers, Decimal, Votes]:  # pragma: no coverage
        ...


def _iter_transferable_ballots(
    ballots: list[PreferenceBallot],
    transfers: Candidates,
    standing: Candidates,
) -> Iterator[tuple[PreferenceBallot, Candidate]]:
    all_candidates = transfers + standing
    for ballot in ballots:
        current_preference = ballot.get_next_preference(all_candidates)
        if current_preference in transfers:
            yield ballot, current_preference


# Currently not used in STVPoll
def transfer_all(
    *,
    ballots: list[PreferenceBallot],
    vote_count: Votes,
    transfers: Candidates,
    standing: Candidates,
    quota: int,
    decrease_value: bool,
) -> tuple[VoteTransfers, Decimal, Votes]:
    """
    Transfer votes for list of candidates or a single candidate.
    If candidate was elected, set decrease_value to True.
    """
    transfer_log = Counter[tuple[Candidate, Candidate]]()
    exhausted = Decimal(0)

    # Go through each transferable ballot (where a candidate is current preference)
    for ballot, candidate in _iter_transferable_ballots(ballots, transfers, standing):
        if decrease_value:
            votes = vote_count[candidate]
            transfer_quota = (votes - quota) / votes
            ballot.decrease_value(transfer_quota)

        if target_candidate := ballot.get_next_preference(standing):
            transfer_log[(candidate, target_candidate)] += ballot.value
        else:
            exhausted += ballot.value

    # Return a completely new current votes dictionary, with new vote values and w/o transferred candidates.
    return (
        transfer_log,
        exhausted,
        {
            candidate: vote_count[candidate]
            + sum(transfer_log[(_from, candidate)] for _from in transfers)
            for candidate in standing
        },
    )


def transfer_serial(
    *,
    ballots: list[PreferenceBallot],
    vote_count: Votes,
    transfers: Candidates,
    standing: Candidates,
    quota: int,
    decrease_value: bool,
) -> tuple[VoteTransfers, Decimal, Votes]:
    """
    Transfer votes for list of candidates or a single candidate.
    If candidate was elected, ballot value should probably be decreased.
    Will generate new current_votes dictionary.
    """
    transfer_log = Counter[tuple[Candidate, Candidate]]()
    exhausted = Decimal(0)

    # We need to know which candidates are still to be transferred
    transfer_queue = list(transfers)
    while transfer_queue:
        candidate = transfer_queue.pop(0)
        votes = vote_count[candidate]
        transfer_quota = (votes - quota) / votes if decrease_value else Decimal(1)

        # Go through each transferable ballot where candidate is current preference
        for ballot, _ in _iter_transferable_ballots(ballots, (candidate,), standing):
            ballot.decrease_value(transfer_quota)
            if target_candidate := ballot.get_next_preference(
                standing + tuple(transfer_queue)
            ):
                transfer_log[(candidate, target_candidate)] += ballot.value
            else:
                exhausted += ballot.value

        # Redo vote count for each vote transfer
        vote_count = {
            target: votes + transfer_log[(candidate, target)]
            for target, votes in vote_count.items()
        }

    # Return final transfer count, without transferred candidates.
    return (
        transfer_log,
        exhausted,
        {candidate: vote_count[candidate] for candidate in standing},
    )
