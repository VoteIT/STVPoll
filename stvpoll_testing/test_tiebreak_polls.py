from stvpoll.abcs import STVPollBase
from stvpoll.result import ElectionResult


def mk_tie_break_that_breaks(factory: type[STVPollBase]) -> STVPollBase:
    example_candidates = ["A", "B", "C", "D", "E", "F"]
    example_ballots = (
        (["A", "D", "C"], 1),
        (["E", "C", "A", "B"], 1),
    )
    poll = factory(seats=3, candidates=example_candidates, random_in_tiebreaks=True)
    for b in example_ballots:
        poll.add_ballot(*b)
    return poll


def mk_multiple_quota_tiebreak(factory: type[STVPollBase]) -> ElectionResult:
    """
    A poll with quota 1, to ensure that multiple candidates reach quota.
    """
    poll = factory(seats=4, candidates=["one", "two", "three", "four", "five", "six"])
    poll.add_ballot(["one", "three"])
    poll.add_ballot(["two", "four"])
    poll.add_ballot(["five", "six"])
    return poll.calculate()


def test_scottish():
    from stvpoll.scottish_stv import ScottishSTV

    poll = mk_tie_break_that_breaks(ScottishSTV)
    result = poll.calculate()
    assert result.randomized
    assert result.complete

    result = mk_multiple_quota_tiebreak(ScottishSTV)
    assert result.complete


def test_cpo():
    from stvpoll.cpo_stv import CPO_STV

    poll = mk_tie_break_that_breaks(CPO_STV)
    result = poll.calculate()
    assert result.randomized
    assert result.complete

    result = mk_multiple_quota_tiebreak(CPO_STV)
    assert result.complete
