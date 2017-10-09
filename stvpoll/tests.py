import unittest

from stvpoll import hagenbach_bischof_quota


def _opa_example_fixture(factory):
    """
    28 voters ranked Alice first, Bob second, and Chris third
    26 voters ranked Bob first, Alice second, and Chris third
    3 voters ranked Chris first
    2 voters ranked Don first
    1 voter ranked Eric first
    """
    obj = factory(seats=3, candidates=['Alice', 'Bob', 'Chris', 'Don', 'Eric'])
    obj.add_ballot(['Alice', 'Bob', 'Chris'], 28)
    obj.add_ballot(['Bob', 'Alice', 'Chris'], 26)
    obj.add_ballot(['Chris'], 3)
    obj.add_ballot(['Don'], 2)
    obj.add_ballot(['Eric'], 1)
    return obj

def _wikipedia_example_fixture(factory):
    """
    Example from https://en.wikipedia.org/wiki/Single_transferable_vote
    """
    example_ballots = (
        (('orange',), 4),
        (('pear', 'orange',), 2),
        (('chocolate', 'strawberry',), 8),
        (('chocolate', 'bonbon',), 4),
        (('strawberry',), 1),
        (('bonbon',), 1),
    )
    obj = factory(seats=3, candidates=('orange', 'chocolate', 'pear', 'strawberry', 'bonbon'))
    for b in example_ballots:
        obj.add_ballot(*b)
    return obj


def _wikipedia_cpo_example_fixture(factory):
    """
    Example from https://en.wikipedia.org/wiki/CPO-STV
    """
    example_candidates = ('Andrea', 'Carter', 'Brad', 'Delilah', 'Scott')
    example_ballots = (
        (('Andrea',), 25),
        (('Carter', 'Brad', 'Delilah'), 34),
        (('Brad', 'Delilah'), 7),
        (('Delilah', 'Brad'), 8),
        (('Delilah', 'Scott'), 5),
        (('Scott', 'Delilah'), 21),
    )
    obj = factory(seats=3, candidates=example_candidates, quota=hagenbach_bischof_quota)
    for b in example_ballots:
        obj.add_ballot(*b)
    return obj


def _some_new_fixture(factory):
    """
    Example from https://en.wikipedia.org/wiki/CPO-STV
    """
    example_candidates = ('Andrea', 'Carter', 'Brad', 'Delilah', 'Scott', 'Johan', 'Batman', 'Robin')
    example_candidates = ('Andrea', 'Batman', 'Robin')
    example_ballots = (
        (('Andrea', 'Batman', 'Robin'), 1),
        (('Robin', 'Andrea', 'Batman'), 1),
        (('Batman', 'Robin', 'Andrea'), 1),
        # (('Carter', 'Brad', 'Batman', 'Robin', 'Delilah'), 34),
        # (('Brad', 'Delilah'), 7),
        # (('Delilah', 'Brad'), 8),
        # (('Batman', 'Delilah', 'Robin', 'Brad'), 8),
        # (('Delilah', 'Johan', 'Brad', 'Batman'), 8),
        # (('Delilah', 'Batman', 'Brad'), 8),
        # (('Delilah', 'Brad', 'Robin'), 8),
        # (('Delilah', 'Scott'), 5),
        # (('Scott', 'Delilah', 'Robin'), 21),
    )
    obj = factory(seats=2, candidates=example_candidates, quota=hagenbach_bischof_quota)
    for b in example_ballots:
        obj.add_ballot(*b)
    return obj


class STVPollBaseTests(unittest.TestCase):

    @property
    def _cut(self):
        from stvpoll import STVPollBase
        return STVPollBase

    def test_ballot_count(self):
        obj = self._cut(seats=0, candidates=('a', 'b'))
        obj.add_ballot(['a', 'b'], 5)
        obj.add_ballot(['a'], 3)
        obj.add_ballot(['b'], 8)
        self.assertEqual(obj.ballot_count, 16)

    def test_add_ballot(self):
        obj = self._cut(seats=0, candidates=('a', 'b'))
        obj.add_ballot(['a', 'b'])
        obj.add_ballot(['a', 'b'])
        obj.add_ballot(['a', 'b'])
        obj.add_ballot(['a'])
        obj.add_ballot(['a'])
        obj.add_ballot(['b'])
        self.assertEqual(set(obj.ballots), set([('a',), ('b',), ('a', 'b')]))
        self.assertEqual(obj.ballot_count, 6)

    def test_verify_ballot(self):
        pass


class ScottishSTVTests(unittest.TestCase):
    opa_results = ('Alice', 'Bob', 'Chris')
    wiki_results = ('chocolate', 'orange', 'strawberry')
    wiki_cpo_results = ('Carter', 'Andrea', 'Scott')

    @property
    def _cut(self):
        from stvpoll.scottish_stv import ScottishSTV
        return ScottishSTV

    def test_opa_example(self):
        obj = _opa_example_fixture(self._cut)
        result = obj.calculate()
#        print(map(str, result.rounds))
        self.assertEqual(result.elected_as_tuple(), self.opa_results)

    def test_wikipedia_example(self):
        obj = _wikipedia_example_fixture(self._cut)
        result = obj.calculate()
#        print(map(str, result.rounds))
        self.assertEqual(result.elected_as_tuple(), self.wiki_results)

    def test_wikipedia_cpo_example(self):
        obj = _wikipedia_cpo_example_fixture(self._cut)
        result = obj.calculate()
#        print(map(str, result.rounds))
        self.assertEqual(result.elected_as_tuple(), self.wiki_cpo_results)

    def test_the_new_one(self):
        obj = _some_new_fixture(self._cut)
        result = obj.calculate()
        print(result.poll.__class__.__name__)
        print(result.elected)
#        self.assertEqual(result.elected_as_tuple(), self.wiki_cpo_results)


class COPSTVTests(ScottishSTVTests):
    wiki_results = ('chocolate', 'orange', 'strawberry')
    wiki_cpo_results = ('Carter', 'Andrea', 'Delilah')

    @property
    def _cut(self):
        from stvpoll.cpo_stv import CPO_STV
        return CPO_STV


if __name__ == "__main__":
    unittest.main()
