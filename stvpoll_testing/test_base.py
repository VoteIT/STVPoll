import pytest

from stvpoll.abcs import STVPollBase
from stvpoll.exceptions import STVException, CandidateDoesNotExist


class DummySTV(STVPollBase):
    def calculate_round(self): ...


def test_ballot_count():
    poll = DummySTV(seats=0, candidates=("a", "b"))
    poll.add_ballot(["a", "b"], 13)
    poll.add_ballot(["b"], 28)
    poll.add_ballot(["a"])
    assert poll.ballot_count == 42


def test_bad_config():
    with pytest.raises(STVException):
        DummySTV(seats=4, candidates=["one", "two", "three"])


def test_candidate_does_not_exist():
    poll = DummySTV(seats=2, candidates=["one", "two", "three"])
    with pytest.raises(CandidateDoesNotExist):
        poll.add_ballot(["a", "b"])
