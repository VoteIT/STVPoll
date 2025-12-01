from stvpoll.abcs import STVPollBase


def mk_wikipedia_example_poll(factory: type[STVPollBase]) -> STVPollBase:
    """
    Example from https://en.wikipedia.org/wiki/Single_transferable_vote
    """
    example_ballots = (
        (("orange",), 4),
        (("pear", "orange"), 2),
        (("chocolate", "strawberry"), 8),
        (("chocolate", "bonbon"), 4),
        (("strawberry",), 1),
        (("bonbon",), 1),
    )
    poll = factory(
        seats=3, candidates=("orange", "chocolate", "pear", "strawberry", "bonbon")
    )
    for b in example_ballots:
        poll.add_ballot(*b)
    return poll


def test_irv():
    from stvpoll.irv import IRV

    poll = mk_wikipedia_example_poll(IRV)
    result = poll.calculate()
    assert result == ["chocolate"]
    assert not result.randomized
    assert result.quota == 11
    assert result.rounds[-1].votes == {
        "orange": 4,
        "chocolate": 12,
        "pear": 2,
        "strawberry": 1,
        "bonbon": 1,
    }


def test_stv():
    from stvpoll.scottish_stv import ScottishSTV

    poll = mk_wikipedia_example_poll(ScottishSTV)
    result = poll.calculate()
    assert result.elected_as_set() == {"chocolate", "strawberry", "orange"}
    assert not result.randomized


def test_cpo():
    from stvpoll.cpo_stv import CPO_STV

    poll = mk_wikipedia_example_poll(CPO_STV)
    result = poll.calculate()
    assert result.elected_as_set() == {"chocolate", "strawberry", "orange"}
    assert not result.randomized


def test_function_based_stv():
    from stvpoll.scottish_stv import calculate_scottish_stv

    candidates = ("orange", "chocolate", "pear", "strawberry", "bonbon")
    result = calculate_scottish_stv(
        candidates=candidates,
        random_shuffle=False,
        votes=(
            (("orange",), 4),
            (("pear", "orange"), 2),
            (("chocolate", "strawberry"), 8),
            (("chocolate", "bonbon"), 4),
            (("strawberry",), 1),
            (("bonbon",), 1),
        ),
        winners=3,
    )
    assert result == ["chocolate", "orange", "strawberry"]
    assert not result.randomized


def test_function_based_irv():
    from stvpoll.irv import calculate_irv

    candidates = ("orange", "chocolate", "pear", "strawberry", "bonbon")
    result = calculate_irv(
        candidates=candidates,
        random_shuffle=False,
        votes=(
            (("orange",), 4),
            (("pear", "orange"), 2),
            (("chocolate", "strawberry"), 8),
            (("chocolate", "bonbon"), 4),
            (("strawberry",), 1),
            (("bonbon",), 1),
        ),
    )
    assert result == ["chocolate"]
    assert not result.randomized
    assert result.quota == 11
    assert result.rounds[-1].votes == {
        "orange": 4,
        "chocolate": 12,
        "pear": 2,
        "strawberry": 1,
        "bonbon": 1,
    }
