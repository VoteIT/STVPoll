from stvpoll.abcs import STVPollBase, ElectionResult
from stvpoll.tiebreak_strategies import TiebreakRandom
from stvpoll.types import Candidates


def recalculate_result(
    poll: STVPollBase, order: Candidates, expected_winners: Candidates = None
) -> ElectionResult:
    """
    Redo poll calculation, and ensure that randomized results follow previous order.
    Use if you have results from a version prior to 0.2.3, where vote counts were mistakenly discarded.
    """
    for tiebreaker in poll.tiebreakers:
        if isinstance(tiebreaker, TiebreakRandom):
            tiebreaker.shuffled = order
            tiebreaker.reversed = tuple(reversed(order))
    result = poll.calculate()
    if expected_winners is not None:
        assert (
            result.elected_as_tuple() == expected_winners
        ), "Result does not match list of expected winners!"
    return result
