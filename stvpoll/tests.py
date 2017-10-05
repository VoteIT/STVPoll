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


class STVPollBaseTests(unittest.TestCase):

    @property
    def _cut(self):
        from stvpoll import STVPollBase
        return STVPollBase

    def test_ballot_count(self):
        obj = self._cut()
        obj.ballots[('a', 'b')] = 5
        obj.ballots[('a',)] = 3
        obj.ballots[('b',)] = 8
        self.assertEqual(obj.ballot_count, 16)

    def test_add_ballot(self):
        obj = self._cut()
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

    @property
    def _cut(self):
        from stvpoll import ScottishSTV
        return ScottishSTV

    def test_opa_example(self):
        obj = _opa_example_fixture(self._cut)
        self.assertEqual(obj.calculate(), ('Alice', 'Bob', 'Chris'))


if __name__ == "__main__":
    unittest.main()