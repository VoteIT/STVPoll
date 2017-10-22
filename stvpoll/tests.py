from __future__ import unicode_literals

import unittest
from random import choice

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
    obj = factory(seats=3, candidates=example_candidates)
    for b in example_ballots:
        obj.add_ballot(*b)
    return obj


def _CPO_extreme_tie_fixture(factory):
    """
    Example from https://en.wikipedia.org/wiki/CPO-STV
    """
    example_candidates = ('Andrea', 'Batman', 'Robin', 'Gorm')
    example_ballots = (
        (('Andrea', 'Batman', 'Robin'), 1),
        (('Robin', 'Andrea', 'Batman'), 1),
        (('Batman', 'Robin', 'Andrea'), 1),
        # (('Andrea'), 1),
        # (('Robin'), 1),
        # (('Batman'), 1),
        (('Gorm',), 2),
    )
    obj = factory(seats=2, candidates=example_candidates)
    for b in example_ballots:
        obj.add_ballot(*b)
    return obj


def _big_fixture(factory):
    import json
    from codecs import open
    with open('stvpoll/70 in 35.json') as infile:
        votedata = json.load(infile)
    # obj = factory(seats=votedata['seats'], candidates=votedata['candidates'])
    obj = factory(seats=5, candidates=votedata['candidates'][:20])
    for b in votedata['ballots']:
        obj.add_ballot(b, 1)
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
    wiki_cpo_results = ('Carter', 'Scott', 'Andrea')

    @property
    def _cut(self):
        from stvpoll.scottish_stv import ScottishSTV
        return ScottishSTV

    def test_opa_example(self):
        obj = _opa_example_fixture(self._cut)
        result = obj.calculate()
#        print(map(str, result.rounds))
        self.assertEqual(result.elected_as_tuple(), self.opa_results)
        self.assertEqual(result.as_dict()['randomized'], False)

    def test_wikipedia_example(self):
        obj = _wikipedia_example_fixture(self._cut)
        result = obj.calculate()
#        print(map(str, result.rounds))
        self.assertEqual(result.elected_as_tuple(), self.wiki_results)
        self.assertEqual(result.as_dict()['randomized'], False)

    def test_wikipedia_cpo_example(self):
        obj = _wikipedia_cpo_example_fixture(self._cut)
        result = obj.calculate()
#        print(map(str, result.rounds))
        self.assertEqual(result.elected_as_tuple(), self.wiki_cpo_results)
        self.assertEqual(result.as_dict()['randomized'], False)

    def test_cpo_tie(self):
        obj = _CPO_extreme_tie_fixture(self._cut)
        result = obj.calculate()
        self.assertEqual(result.as_dict()['randomized'], True)
        self.assertEqual(result.as_dict()['complete'], True)

    # def test_big(self):
    #     obj = _big_fixture(self._cut)
    #     result = obj.calculate()
    #     print('Big runtime ({}): {} seconds'.format(obj.__class__.__name__, result.runtime))


class COPSTVTests(ScottishSTVTests):
    wiki_cpo_results = ('Carter', 'Andrea', 'Delilah')

    @property
    def _cut(self):
        from stvpoll.cpo_stv import CPO_STV
        return CPO_STV


if __name__ == "__main__":
    unittest.main()
