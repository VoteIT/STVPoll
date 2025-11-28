from typing import Protocol


class Quota(Protocol):
    """Calculate poll quota from valid ballot count and expected poll winners"""

    def __call__(self, ballot_count: int, winners: int) -> int:  # pragma: no coverage
        ...


# Used in CPO STV
def hagenbach_bischof_quota(ballot_count: int, winners: int) -> int:
    """
    Calculate poll quota from ballot count and expected poll winners
    >>> hagenbach_bischof_quota(100, 3)
    25
    """
    return ballot_count // (winners + 1)


def droop_quota(ballot_count: int, winners: int) -> int:
    """
    Used in Scottish STV
    Calculate poll quota from ballot count and expected poll winners
    >>> droop_quota(100, 3)
    26
    """
    return hagenbach_bischof_quota(ballot_count, winners) + 1


def hare_quota(ballot_count: int, winners: int) -> int:
    """
    Not currently used in implementations
    Calculate poll quota from ballot count and expected poll winners
    >>> hare_quota(100, 3)
    33
    """
    return ballot_count // winners
