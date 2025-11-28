from random import seed


def test_wikipedia_cpo_example_poll():
    """
    Example from https://en.wikipedia.org/wiki/CPO-STV
    """
    from stvpoll.cpo_stv import CPO_STV

    example_candidates = ("Andrea", "Carter", "Brad", "Delilah", "Scott")
    example_ballots = (
        (("Andrea",), 25),
        (("Carter", "Brad", "Delilah"), 34),
        (("Brad", "Delilah"), 7),
        (("Delilah", "Brad"), 8),
        (("Delilah", "Scott"), 5),
        (("Scott", "Delilah"), 21),
    )
    poll = CPO_STV(seats=3, candidates=example_candidates)
    for b in example_ballots:
        poll.add_ballot(*b)
    result = poll.calculate()
    assert result.elected_as_set() == {"Carter", "Andrea", "Delilah"}
    assert not result.randomized


def test_cpo_extreme_tie():
    """
    Example from https://en.wikipedia.org/wiki/CPO-STV
    """
    from stvpoll.cpo_stv import CPO_STV

    seed(42)
    example_candidates = ("Andrea", "Batman", "Robin", "Gorm")
    example_ballots = (
        (("Andrea", "Batman", "Robin"), 1),
        (("Robin", "Andrea", "Batman"), 1),
        (("Batman", "Robin", "Andrea"), 1),
        (("Gorm",), 2),
    )
    poll = CPO_STV(seats=2, candidates=example_candidates)
    for b in example_ballots:
        poll.add_ballot(*b)
    result = poll.calculate()
    assert result.randomized
    assert result.complete
    assert result.empty_ballot_count == 0
    assert result.elected_as_tuple() == ("Gorm", "Andrea")


def test_all_wins():
    from stvpoll.cpo_stv import CPO_STV

    poll = CPO_STV(seats=2, candidates=["one", "two"])
    result = poll.calculate()
    assert result.complete


def test_tiebreak_history():
    """Unreasonably high quota"""
    from stvpoll.cpo_stv import CPO_STV

    example_candidates = ("Andrea", "Robin", "Gorm")
    example_ballots = (
        (("Andrea",), 3),
        (("Robin",), 2),
        (("Gorm", "Robin"), 1),
        ((), 3),
    )
    poll = CPO_STV(seats=1, candidates=example_candidates, quota=lambda x, y: 100)
    for b in example_ballots:
        poll.add_ballot(*b)
    result = poll.calculate()
    assert result.randomized
    assert result.complete
    assert result.empty_ballot_count == 3


def test_all_elected():
    """All candidates elected on base quote"""
    from stvpoll.cpo_stv import CPO_STV

    example_candidates = ("Andrea", "Robin", "Gorm")
    example_ballots = (
        (("Andrea",), 2),
        (("Robin",), 2),
        (("Gorm",), 1),
    )
    poll = CPO_STV(seats=2, candidates=example_candidates, quota=lambda x, y: 1)
    for b in example_ballots:
        poll.add_ballot(*b)
    result = poll.calculate()
    assert not result.randomized
    assert result.complete
