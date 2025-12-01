from random import seed

import pytest

from stvpoll.exceptions import STVException


def test_wikipedia_cpo_example_poll():
    """
    Example from https://en.wikipedia.org/wiki/CPO-STV
    """
    from stvpoll.cpo_stv import CPO_STV, calculate_cpo_stv

    example_candidates = ("Andrea", "Carter", "Brad", "Delilah", "Scott")
    example_ballots = (
        (("Andrea",), 25),
        (("Carter", "Brad", "Delilah"), 34),
        (("Brad", "Delilah"), 7),
        (("Delilah", "Brad"), 8),
        (("Delilah", "Scott"), 5),
        (("Scott", "Delilah"), 21),
    )
    # Class based
    poll = CPO_STV(seats=3, candidates=example_candidates)
    for b in example_ballots:
        poll.add_ballot(*b)
    result = poll.calculate()
    assert result.elected_as_set() == {"Carter", "Andrea", "Delilah"}
    assert not result.randomized
    # Function based
    result = calculate_cpo_stv(example_candidates, example_ballots, 3)
    assert result.elected_as_set() == {"Carter", "Andrea", "Delilah"}
    assert not result.randomized


def test_too_few_candidates():
    from stvpoll.cpo_stv import calculate_cpo_stv

    with pytest.raises(STVException):
        calculate_cpo_stv((), (), 2)


def test_cpo_extreme_tie():
    from stvpoll.cpo_stv import CPO_STV, calculate_cpo_stv

    example_candidates = ("Andrea", "Batman", "Robin", "Fjodor")
    example_ballots = (
        (("Andrea", "Batman", "Robin"), 1),
        (("Robin", "Andrea", "Batman"), 1),
        (("Batman", "Robin", "Andrea"), 1),
        (("Fjodor",), 2),
    )
    # Class based
    seed(42)
    poll = CPO_STV(seats=2, candidates=example_candidates)
    for b in example_ballots:
        poll.add_ballot(*b)
    result = poll.calculate()
    assert result.randomized
    assert result.complete
    assert result.empty_ballot_count == 0
    assert result.elected_as_tuple() == ("Fjodor", "Andrea")
    # Function based
    result = calculate_cpo_stv(example_candidates, example_ballots, 2)
    assert result.randomized
    assert result.complete
    assert result.empty_ballot_count == 0
    assert result.elected_as_tuple() == ("Andrea", "Fjodor")


def test_all_wins():
    from stvpoll.cpo_stv import CPO_STV, calculate_cpo_stv

    # Class based
    poll = CPO_STV(seats=2, candidates=["one", "two"])
    result = poll.calculate()
    assert result.complete
    # Function based
    result = calculate_cpo_stv(("one", "two"), (), 2)
    assert result.complete


def test_tiebreak_history():
    """Unreasonably high quota"""
    from stvpoll.cpo_stv import CPO_STV, calculate_cpo_stv

    example_candidates = ("Andrea", "Robin", "Gorm")
    example_ballots = (
        (("Andrea",), 3),
        (("Robin",), 2),
        (("Gorm", "Robin"), 1),
        ((), 3),
    )
    # Class based
    poll = CPO_STV(seats=1, candidates=example_candidates, quota=lambda x, y: 100)
    for b in example_ballots:
        poll.add_ballot(*b)
    result = poll.calculate()
    assert result.randomized
    assert result.complete
    assert result.empty_ballot_count == 3
    # Function based
    result = calculate_cpo_stv(
        example_candidates, example_ballots, 1, quota_method=lambda x, y: 100
    )
    assert result.randomized
    assert result.complete
    assert result.empty_ballot_count == 3


def test_all_elected():
    """All candidates elected on base quote"""
    from stvpoll.cpo_stv import CPO_STV, calculate_cpo_stv

    example_candidates = ("Andrea", "Robin", "Gorm")
    example_ballots = (
        (("Andrea",), 2),
        (("Robin",), 2),
        (("Gorm",), 1),
    )
    # Class based
    poll = CPO_STV(seats=2, candidates=example_candidates, quota=lambda x, y: 1)
    for b in example_ballots:
        poll.add_ballot(*b)
    result = poll.calculate()
    assert not result.randomized
    assert result.complete
    # Function based
    result = calculate_cpo_stv(
        example_candidates, example_ballots, 2, quota_method=lambda x, y: 1
    )
    assert not result.randomized
    assert result.complete
