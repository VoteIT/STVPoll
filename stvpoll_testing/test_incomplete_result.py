from stvpoll.abcs import STVPollBase


def mk_incomplete_result_poll(factory: type[STVPollBase]) -> STVPollBase:
    example_candidates = ("Andrea", "Batman", "Robin", "Gorm")
    example_ballots = (
        (("Batman",), 1),
        (("Gorm",), 2),
    )
    poll = factory(seats=3, candidates=example_candidates, random_in_tiebreaks=False)
    for b in example_ballots:
        poll.add_ballot(*b)
    return poll


def test_irv():
    from stvpoll.irv import IRV

    poll = IRV(candidates=(1, 2, 3))
    result = poll.calculate()
    assert not result.complete


def test_stv():
    from stvpoll.scottish_stv import ScottishSTV

    poll = mk_incomplete_result_poll(ScottishSTV)
    result = poll.calculate()
    assert not result.randomized
    assert not result.complete


def test_cpo():
    from stvpoll.cpo_stv import CPO_STV

    poll = mk_incomplete_result_poll(CPO_STV)
    result = poll.calculate()
    assert not result.randomized
    assert not result.complete
