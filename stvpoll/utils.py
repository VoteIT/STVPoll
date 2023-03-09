from stvpoll.abcs import STVPollBase, ElectionResult
from stvpoll.tiebreak_strategies import TiebreakRandom
from stvpoll.types import Candidates, ResultDict, CandidateStatus


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


def result_dict_to_order(result: ResultDict) -> Candidates:
    """
    Generate an ordered list of candidates from an existing result.
    For use in recalculate_result().
    """

    def get_reverse_excluded():
        for _round in reversed(result["rounds"]):
            if _round["status"] == CandidateStatus.Excluded:
                yield from _round["selected"]

    winner_order = result["winners"]
    excluded_reverse_order = tuple(get_reverse_excluded())
    missing = tuple(
        set(result["candidates"]) - set(winner_order) - set(excluded_reverse_order)
    )
    return winner_order + missing + excluded_reverse_order
