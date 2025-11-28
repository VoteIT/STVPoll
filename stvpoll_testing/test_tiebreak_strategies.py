from decimal import Decimal
from random import seed


def test_random():
    from stvpoll.tiebreak_strategies import TiebreakRandom

    seed(42)
    strategy = TiebreakRandom((1, 2, 3))
    assert strategy.get_result_dict() == {}
    assert strategy.resolve((2, 3), ()) == 3
    assert strategy.resolve((2, 3), (), lowest=True) == 2
    assert strategy.get_result_dict() == {"randomized": True, "random_order": (3, 1, 2)}


def test_history():
    from stvpoll.tiebreak_strategies import TiebreakHistory

    strategy = TiebreakHistory()
    assert strategy.resolve((2, 3), ({2: Decimal(1), 3: Decimal(1)},)) == (2, 3), (
        "Still tied"
    )
    assert strategy.resolve((2, 3), ({2: Decimal(2), 3: Decimal(1)},)) == 2, (
        "Highest returned"
    )
    assert (
        strategy.resolve((2, 3), ({2: Decimal(2), 3: Decimal(1)},), lowest=True) == 3
    ), "Lowest returned"
    assert (
        strategy.resolve(
            (2, 3),
            (
                {2: Decimal(4), 3: Decimal(4)},
                {2: Decimal(3), 3: Decimal(3)},
                {2: Decimal(2), 3: Decimal(1)},
            ),
        )
        == 2
    ), "Multiple history rounds"
