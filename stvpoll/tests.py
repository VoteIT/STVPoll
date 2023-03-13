from __future__ import annotations

import random
import unittest
from decimal import Decimal

from stvpoll.abcs import STVPollBase
from stvpoll.scottish_stv import ScottishSTV
from stvpoll.cpo_stv import CPO_STV
from typing import Type


def _opa_example_fixture(factory: Type[STVPollBase]) -> STVPollBase:
    """
    28 voters ranked Alice first, Bob second, and Chris third
    26 voters ranked Bob first, Alice second, and Chris third
    3 voters ranked Chris first
    2 voters ranked Don first
    1 voter ranked Eric first
    """
    obj = factory(seats=3, candidates=["Alice", "Bob", "Chris", "Don", "Eric"])
    obj.add_ballot(["Alice", "Bob", "Chris"], 28)
    obj.add_ballot(["Bob", "Alice", "Chris"], 26)
    obj.add_ballot(["Chris"], 3)
    obj.add_ballot(["Don"], 2)
    obj.add_ballot(["Eric"], 1)
    return obj


def _wikipedia_example_fixture(factory: Type[STVPollBase]) -> STVPollBase:
    """
    Example from https://en.wikipedia.org/wiki/Single_transferable_vote
    """
    example_ballots = (
        (("orange",), 4),
        (
            (
                "pear",
                "orange",
            ),
            2,
        ),
        (
            (
                "chocolate",
                "strawberry",
            ),
            8,
        ),
        (
            (
                "chocolate",
                "bonbon",
            ),
            4,
        ),
        (("strawberry",), 1),
        (("bonbon",), 1),
    )
    obj = factory(
        seats=3, candidates=("orange", "chocolate", "pear", "strawberry", "bonbon")
    )
    for b in example_ballots:
        obj.add_ballot(*b)
    return obj


def _wikipedia_cpo_example_fixture(factory: Type[STVPollBase]) -> STVPollBase:
    """
    Example from https://en.wikipedia.org/wiki/CPO-STV
    """
    example_candidates = ("Andrea", "Carter", "Brad", "Delilah", "Scott")
    example_ballots = (
        (("Andrea",), 25),
        (("Carter", "Brad", "Delilah"), 34),
        (("Brad", "Delilah"), 7),
        (("Delilah", "Brad"), 8),
        (("Delilah", "Scott"), 5),
        (("Scott", "Delilah"), 21),
    )
    obj = factory(seats=3, candidates=example_candidates)
    for b in example_ballots:
        obj.add_ballot(*b)
    return obj


def _CPO_extreme_tie_fixture(factory: Type[STVPollBase]) -> STVPollBase:
    """
    Example from https://en.wikipedia.org/wiki/CPO-STV
    """
    example_candidates = ("Andrea", "Batman", "Robin", "Gorm")
    example_ballots = (
        (("Andrea", "Batman", "Robin"), 1),
        (("Robin", "Andrea", "Batman"), 1),
        (("Batman", "Robin", "Andrea"), 1),
        (("Gorm",), 2),
    )
    obj = factory(seats=2, candidates=example_candidates)
    for b in example_ballots:
        obj.add_ballot(*b)
    return obj


def _scottish_tiebreak_history_fixture(factory: Type[STVPollBase]) -> STVPollBase:
    """
    Example from https://en.wikipedia.org/wiki/CPO-STV
    """
    example_candidates = ("Andrea", "Robin", "Gorm")
    example_ballots = (
        (("Andrea",), 3),
        (("Robin",), 2),
        (("Gorm", "Robin"), 1),
        ((), 3),
    )
    obj = factory(seats=1, candidates=example_candidates, quota=lambda x, y: 100)
    for b in example_ballots:
        obj.add_ballot(*b)
    return obj


def _incomplete_result_fixture(factory: Type[STVPollBase]) -> STVPollBase:
    """
    Example from https://en.wikipedia.org/wiki/CPO-STV
    """
    example_candidates = ("Andrea", "Batman", "Robin", "Gorm")
    example_ballots = (
        (("Batman",), 1),
        (("Gorm",), 2),
    )
    obj = factory(seats=3, candidates=example_candidates, random_in_tiebreaks=False)
    for b in example_ballots:
        obj.add_ballot(*b)
    return obj


def _tie_break_that_breaks(factory: Type[STVPollBase]) -> STVPollBase:
    example_candidates = ["A", "B", "C", "D", "E", "F"]
    example_ballots = (
        (["A", "D", "C"], 1),
        (["E", "C", "A", "B"], 1),
    )
    obj = factory(seats=3, candidates=example_candidates, random_in_tiebreaks=True)
    for b in example_ballots:
        obj.add_ballot(*b)
    return obj


def _vote_transfers_check(factory: Type[STVPollBase]) -> STVPollBase:
    candidates = (6041, 6042, 6044, 6038, 6034, 6043, 6040, 6039, 6035, 6036, 6037)
    ballots = [
        [6039, 6043, 6042, 6044, 6034],
        [6043, 6042, 6039, 6036, 6037, 6044, 6041, 6040, 6038, 6035, 6034],
        [6038, 6042, 6036, 6035, 6034, 6037, 6040, 6039, 6043, 6044, 6041],
        [6034, 6035, 6036, 6037, 6038],
        [6037, 6038, 6044],
        [6039, 6038, 6037, 6042, 6044],
        [6038, 6039, 6037, 6036, 6035, 6034, 6040, 6042],
        [6036, 6035, 6039, 6040, 6042, 6037, 6041, 6043, 6044],
        [6034, 6038, 6039, 6040, 6042],
        [6034, 6036, 6035, 6040, 6042, 6043, 6044, 6041, 6039, 6037, 6038],
        [6037, 6042, 6040, 6044, 6035],
        [6034, 6042, 6037, 6044, 6036, 6035, 6043, 6040, 6039, 6041, 6038],
        [6037, 6043, 6038, 6035, 6034, 6036, 6039, 6040, 6041, 6042, 6044],
        [6036, 6035, 6034, 6038, 6041, 6042, 6040],
        [6037, 6044, 6042, 6040, 6034, 6036, 6035, 6038, 6041],
    ]
    poll = factory(
        seats=5,
        candidates=candidates,
        random_in_tiebreaks=True,
        pedantic_order=True,
    )
    for b in ballots:
        poll.add_ballot(b)
    return poll


class STVPollBaseTests(unittest.TestCase):
    @property
    def _cut(self):
        from stvpoll.scottish_stv import ScottishSTV

        return ScottishSTV

    def test_ballot_count(self):
        obj = self._cut(seats=0, candidates=("a", "b"))
        obj.add_ballot(["a", "b"], 5)
        obj.add_ballot(["a"], 3)
        obj.add_ballot(["b"], 8)
        self.assertEqual(obj.ballot_count, 16)

    def test_add_ballot(self):
        obj = self._cut(seats=0, candidates=("a", "b"))
        obj.add_ballot(["a", "b"])
        obj.add_ballot(["a", "b"])
        obj.add_ballot(["a", "b"])
        obj.add_ballot(["a"])
        obj.add_ballot(["a"])
        obj.add_ballot(["b"])
        self.assertEqual(obj.ballot_count, 6)


class ScottishSTVTests(unittest.TestCase):
    opa_results = {"Alice", "Bob", "Chris"}
    wiki_results = {"chocolate", "strawberry", "orange"}
    wiki_cpo_results = {"Carter", "Scott", "Andrea"}

    @property
    def _cut(self) -> Type[ScottishSTV]:
        return ScottishSTV

    def multiple_only(self):
        if not self._cut.multiple_winners:
            self.skipTest("Only with multiple winner methods")

    def test_opa_example(self):
        obj = _opa_example_fixture(self._cut)
        result = obj.calculate()
        self.assertEqual(result.elected_as_set(), self.opa_results)
        self.assertEqual(result.as_dict()["randomized"], False)

    def test_wikipedia_example(self):
        obj = _wikipedia_example_fixture(self._cut)
        result = obj.calculate()
        self.assertEqual(result.elected_as_set(), self.wiki_results)
        self.assertEqual(result.as_dict()["randomized"], False)

    def test_wikipedia_cpo_example(self):
        obj = _wikipedia_cpo_example_fixture(self._cut)
        result = obj.calculate()
        self.assertEqual(result.elected_as_set(), self.wiki_cpo_results)
        self.assertEqual(result.as_dict()["randomized"], False)

    def test_tiebreak_randomized(self):
        self.multiple_only()
        random.seed(42)
        obj = _CPO_extreme_tie_fixture(self._cut)
        result = obj.calculate()
        result_dict = result.as_dict()
        self.assertEqual(result_dict["randomized"], True)
        self.assertEqual(result_dict["complete"], True)
        self.assertEqual(result_dict["empty_ballot_count"], 0)
        self.assertEqual(result.elected_as_tuple(), ("Gorm", "Andrea"))

    def test_scottish_tiebreak_history(self):
        self.multiple_only()
        obj = _scottish_tiebreak_history_fixture(self._cut)
        result = obj.calculate()
        try:
            self.assertEqual(
                result.as_dict()["randomized"], not isinstance(obj, ScottishSTV)
            )
            self.assertEqual(result.as_dict()["complete"], True)
            self.assertEqual(result.as_dict()["empty_ballot_count"], 3)
        except AttributeError:
            import pdb

            pdb.set_trace()

    def test_incomplete_result(self):
        self.multiple_only()
        obj = _incomplete_result_fixture(self._cut)
        result = obj.calculate()
        self.assertEqual(result.as_dict()["randomized"], False)
        self.assertEqual(result.as_dict()["complete"], False)

    def test_tie_break_that_breaks(self):
        self.multiple_only()
        obj = _tie_break_that_breaks(self._cut)
        result = obj.calculate()
        self.assertEqual(result.as_dict()["randomized"], True)
        self.assertEqual(result.as_dict()["complete"], True)
        self.assertEqual(obj.complete, True)

    def test_multiple_quota_tiebreak(self):
        self.multiple_only()
        poll = self._cut(
            seats=4, candidates=["one", "two", "three", "four", "five", "six"]
        )
        poll.add_ballot(["one", "three"])
        poll.add_ballot(["two", "four"])
        poll.add_ballot(["five", "six"])
        result = poll.calculate()
        self.assertTrue(result.complete)

    def test_exceptions(self):
        self.multiple_only()
        from stvpoll.exceptions import STVException
        from stvpoll.exceptions import CandidateDoesNotExist

        with self.assertRaises(STVException):
            self._cut(seats=3, candidates=(1, 2))
        with self.assertRaises(CandidateDoesNotExist):
            obj = self._cut(seats=3, candidates=(1, 2, 3))
            obj.add_ballot([1, 4])

    def test_randomization_disabled(self):
        self.multiple_only()
        poll = self._cut(
            seats=2,
            candidates=[1, 2, 3],
            random_in_tiebreaks=False,
            pedantic_order=True,
        )
        poll.add_ballot([1, 2], 2)
        poll.add_ballot([2, 1], 2)
        poll.add_ballot([3], 1)
        result = poll.calculate()
        self.assertEqual(result.complete, not isinstance(poll, ScottishSTV))

    def test_no_pedantic_order(self):
        self.multiple_only()
        poll = self._cut(
            seats=2,
            candidates=[1, 2, 3],
            random_in_tiebreaks=False,
        )
        poll.add_ballot([1, 2], 2)
        poll.add_ballot([2, 1], 2)
        poll.add_ballot([3], 1)
        result = poll.calculate()
        self.assertEqual(result.complete, True)

    def test_bad_config(self):
        self.multiple_only()
        from stvpoll.exceptions import STVException

        self.assertRaises(
            STVException, self._cut, seats=4, candidates=["one", "two", "three"]
        )

    def test_vote_transfers(self):
        if not self._cut is ScottishSTV:
            self.skipTest("Only in scottland :)")
        random.seed(42)
        poll = _vote_transfers_check(self._cut)
        result = poll.calculate()
        self.assertEqual(poll.quota, 3)
        self.assertEqual(result.rounds[1].votes[6038], Decimal(2.5))


class CPOSTVTests(ScottishSTVTests):
    wiki_cpo_results = {"Carter", "Andrea", "Delilah"}

    @property
    def _cut(self):
        return CPO_STV

    def test_all_wins(self):
        poll = self._cut(seats=2, candidates=["one", "two"])
        poll.calculate()
        self.assertIs(poll.complete, True)

    def test_possible_combinations(self):
        self.assertEqual(CPO_STV.possible_combinations(5, 2), 10)


class TiebreakTests(unittest.TestCase):
    def test_random(self):
        from .tiebreak_strategies import TiebreakRandom

        random.seed(42)
        strategy = TiebreakRandom((1, 2, 3))
        self.assertEqual(strategy.get_result_dict(), {})
        self.assertEqual(strategy.resolve((2, 3), ()), 3)
        self.assertEqual(strategy.resolve((2, 3), (), lowest=True), 2)
        self.assertEqual(
            strategy.get_result_dict(), {"randomized": True, "random_order": (3, 1, 2)}
        )

    def test_history(self):
        from .tiebreak_strategies import TiebreakHistory

        strategy = TiebreakHistory()
        self.assertEqual(
            strategy.resolve((2, 3), ({2: Decimal(1), 3: Decimal(1)},)),
            (2, 3),
            "All tied up",
        )
        self.assertEqual(
            strategy.resolve((2, 3), ({2: Decimal(2), 3: Decimal(1)},)),
            2,
            "Highest returned",
        )
        self.assertEqual(
            strategy.resolve((2, 3), ({2: Decimal(2), 3: Decimal(1)},), lowest=True),
            3,
            "Lowest returned",
        )
        self.assertEqual(
            strategy.resolve(
                (2, 3),
                (
                    {2: Decimal(4), 3: Decimal(4)},
                    {2: Decimal(3), 3: Decimal(3)},
                    {2: Decimal(2), 3: Decimal(1)},
                ),
            ),
            2,
            "Multiple history rounds",
        )


class IRVTests(ScottishSTVTests):
    wiki_results = {"chocolate"}
    wiki_cpo_results = set()
    opa_results = {"Alice"}

    @property
    def _cut(self):
        from .irv import IRV

        return IRV


class RecalculateTests(unittest.TestCase):
    def _calculate_result(self, expected_winners=None):
        from .utils import recalculate_result

        random.seed(2)
        poll = _CPO_extreme_tie_fixture(ScottishSTV)
        return recalculate_result(
            poll,
            ("Gorm", "Robin", "Andrea", "Batman"),
            expected_winners,
        )

    def test_recalculate(self):
        self.assertEqual(
            self._calculate_result().elected_as_tuple(),
            ("Gorm", "Robin"),
            "Expected result mismatch",
        )

    def test_expected_winners(self):
        self.assertTrue(
            self._calculate_result(("Gorm", "Robin")),
            "Expected result mismatch",
        )
        with self.assertRaises(AssertionError):
            self._calculate_result(("Robin", "Gorm"))

    def test_result_to_order(self):
        from .utils import result_dict_to_order

        order = result_dict_to_order(
            {
                "candidates": (9, 8, 7, 5, 4, 6, 3, 2, 1),
                "rounds": (
                    {"status": "Excluded", "selected": (9,)},
                    {"status": "Elected", "selected": (1,)},
                    {"status": "Excluded", "selected": (8,)},
                    {"status": "Elected", "selected": (2,)},
                    {"status": "Excluded", "selected": (7,)},
                    {"status": "Elected", "selected": (3,)},
                ),
                "winners": (1, 2, 3),
            }
        )
        self.assertEqual(order[:3], (1, 2, 3), "Poll winners")
        self.assertSetEqual(
            set(order[3:6]),
            {4, 5, 6},
            "Unknown order for candidates not in winners or excluded",
        )
        self.assertEqual(
            order[6:], (7, 8, 9), "Excluded candidates in reverse exclusion order"
        )


class TransferStrategiesTests(unittest.TestCase):
    def test_transfer_all(self):
        from .transfer_strategies import transfer_all
        from .abcs import PreferenceBallot

        def rounder(x):
            return x

        ballots = [
            PreferenceBallot((1, 2, 3), 4, rounder),
            PreferenceBallot((2, 3), 2, rounder),
            PreferenceBallot((3,), 1, rounder),
            PreferenceBallot((1,), 1, rounder),
        ]

        transfers, exhausted, votes = transfer_all(
            ballots=ballots,
            vote_count={
                1: Decimal(5),
                2: Decimal(2),
                3: Decimal(1),
            },
            transfers=(1, 2),
            standing=(3,),
            quota=2,
            decrease_value=True,
        )
        self.assertDictEqual(
            transfers,
            {(1, 3): Decimal("2.4"), (2, 3): Decimal(0)},
            "transfer_quota: (5-2)/5=0.6, transfer value: 4*tq",
        )
        self.assertEqual(exhausted, Decimal(".6"))
        self.assertDictEqual(votes, {3: Decimal("3.4")})
        self.assertEqual(ballots[0].multiplier, Decimal("0.6"))
        self.assertEqual(ballots[1].multiplier, Decimal(0))

    def test_transfer_serial(self):
        from .transfer_strategies import transfer_serial
        from .abcs import PreferenceBallot

        def rounder(x):
            return round(x, 3)

        ballots = [
            PreferenceBallot((1, 2, 3), 4, rounder),
            PreferenceBallot((2, 3), 2, rounder),
            PreferenceBallot((3,), 1, rounder),
            PreferenceBallot((1,), 1, rounder),
        ]

        transfers, exhausted, votes = transfer_serial(
            ballots=ballots,
            vote_count={
                1: Decimal(5),
                2: Decimal(2),
                3: Decimal(1),
            },
            transfers=(1, 2),
            standing=(3,),
            quota=2,
            decrease_value=True,
        )
        self.assertEqual(exhausted, Decimal(".6"))
        self.assertDictEqual(
            transfers,
            {(1, 2): Decimal("2.400"), (2, 3): Decimal("2.398")},
        )
        self.assertEqual(
            ballots[1].multiplier,
            Decimal("0.545"),
            "(4.4-2)/4.4 = 0.545",
        )
        self.assertEqual(
            ballots[0].multiplier,
            Decimal("0.327"),
            "0.6*0.54545 = 0.327",
        )
        self.assertDictEqual(votes, {3: Decimal("3.398")})


if __name__ == "__main__":
    unittest.main()
