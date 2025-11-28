from stvpoll.abcs import STVPollBase


def mk_opa_example_poll(factory: type[STVPollBase]) -> STVPollBase:
    """
    28 voters ranked Alice first, Bob second, and Chris third
    26 voters ranked Bob first, Alice second, and Chris third
    3 voters ranked Chris first
    2 voters ranked Don first
    1 voter ranked Eric first
    """
    poll = factory(seats=3, candidates=["Alice", "Bob", "Chris", "Don", "Eric"])
    poll.add_ballot(["Alice", "Bob", "Chris"], 28)
    poll.add_ballot(["Bob", "Alice", "Chris"], 26)
    poll.add_ballot(["Chris"], 3)
    poll.add_ballot(["Don"], 2)
    poll.add_ballot(["Eric"], 1)
    return poll


def test_irv():
    from stvpoll.irv import IRV

    poll = mk_opa_example_poll(IRV)
    result = poll.calculate()
    assert result.elected_as_set() == {"Alice"}
    assert not result.randomized


def test_stv():
    from stvpoll.scottish_stv import ScottishSTV

    poll = mk_opa_example_poll(ScottishSTV)
    result = poll.calculate()
    assert result.elected_as_set() == {"Alice", "Bob", "Chris"}
    assert not result.randomized


def test_cpo():
    from stvpoll.cpo_stv import CPO_STV

    poll = mk_opa_example_poll(CPO_STV)
    result = poll.calculate()
    assert result.elected_as_set() == {"Alice", "Bob", "Chris"}
    assert not result.randomized
