from random import seed

import pytest


class TestRecalculate:
    def recalculate_result(self, expected_winners=None):
        from stvpoll.utils import recalculate_result
        from stvpoll.scottish_stv import ScottishSTV

        example_candidates = ("Andrea", "Batman", "Robin", "Gorm")
        example_ballots = (
            (("Andrea", "Batman", "Robin"), 1),
            (("Robin", "Andrea", "Batman"), 1),
            (("Batman", "Robin", "Andrea"), 1),
            (("Gorm",), 2),
        )
        poll = ScottishSTV(seats=2, candidates=example_candidates)
        for b in example_ballots:
            poll.add_ballot(*b)
        seed(2)
        return recalculate_result(
            poll,
            ("Gorm", "Robin", "Andrea", "Batman"),
            expected_winners,
        )

    def test_recalculate(self):
        assert self.recalculate_result().elected_as_tuple() == ("Gorm", "Robin"), (
            "Expected result mismatch"
        )

    def test_expected_winners(self):
        assert self.recalculate_result(("Gorm", "Robin")), "Expected result mismatch"
        with pytest.raises(AssertionError):
            self.recalculate_result(("Robin", "Gorm"))

    def test_result_to_order(self):
        from stvpoll.utils import result_dict_to_order

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
        assert order[:3] == (1, 2, 3), "Poll winners"
        assert set(order[3:6]) == {4, 5, 6}, (
            "Unknown order for candidates not in winners or excluded"
        )
        assert order[6:] == (7, 8, 9), "Excluded candidates in reverse exclusion order"
