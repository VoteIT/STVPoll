import unittest


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
    obj = factory(seats = 3, candidates=('orange', 'chocolate', 'pear', 'strawberry', 'bonbon'))
    for b in example_ballots:
        obj.add_ballot(*b)
    return obj


class STVPollBaseTests(unittest.TestCase):

    @property
    def _cut(self):
        from stvpoll import STVPollBase
        return STVPollBase

    # TODO: Unbreak Robins code ;)
    # def test_ballot_count(self):
    #     obj = self._cut()
    #     obj.add_ballot(['a', 'b'], 5)
    #     obj.add_ballot(['a'], 3)
    #     obj.add_ballot(['b'], 8)
    #     self.assertEqual(obj.ballot_count, 16)
    #
    # def test_add_ballot(self):
    #     obj = self._cut()
    #     obj.add_ballot(['a', 'b'])
    #     obj.add_ballot(['a', 'b'])
    #     obj.add_ballot(['a', 'b'])
    #     obj.add_ballot(['a'])
    #     obj.add_ballot(['a'])
    #     obj.add_ballot(['b'])
    #     self.assertEqual(set(obj.ballots), set([('a',), ('b',), ('a', 'b')]))
    #     self.assertEqual(obj.ballot_count, 6)
    #
    # def test_verify_ballot(self):
    #     pass


class ScottishSTVTests(unittest.TestCase):

    @property
    def _cut(self):
        # type: () -> STVPollBase
        from stvpoll import ScottishSTV
        return ScottishSTV

    def test_opa_example(self):
        obj = _opa_example_fixture(self._cut)
        self.assertEqual(obj.calculate().elected_as_tuple(), ('Alice', 'Bob', 'Chris'))

    def test_wikipedia_example(self):
        obj = _wikipedia_example_fixture(self._cut)
        self.assertEqual(obj.calculate().elected_as_tuple(), ('chocolate', 'orange', 'strawberry'))


if __name__ == "__main__":
    unittest.main()