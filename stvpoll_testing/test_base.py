from collections import Counter

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
    from stvpoll.base import calculate_stv
    from stvpoll.transfer_strategies import transfer_serial
    from stvpoll.quotas import droop_quota

    candidates = ("a", "b", "c")

    with pytest.raises(STVException):
        DummySTV(seats=4, candidates=candidates)
    with pytest.raises(STVException):
        calculate_stv(
            candidates=candidates,
            tiebreak_strategies=(),
            transfer_strategy=transfer_serial,
            ballots=(),
            winners=4,  # Not enough candidates
            quota_method=droop_quota,
        )


def test_bad_vote():
    from stvpoll.base import calculate_stv
    from stvpoll.transfer_strategies import transfer_serial
    from stvpoll.quotas import droop_quota

    with pytest.raises(STVException):
        calculate_stv(
            candidates=("a", "b", "c"),
            tiebreak_strategies=(),
            transfer_strategy=transfer_serial,
            ballots=[(["d"], 1)],  # Invalid vote
            winners=2,
            quota_method=droop_quota,
        )


def test_no_tiebreak():
    from stvpoll.base import calculate_stv
    from stvpoll.transfer_strategies import transfer_serial
    from stvpoll.quotas import droop_quota

    result = calculate_stv(
        candidates=("a", "b", "c"),
        tiebreak_strategies=(),
        transfer_strategy=transfer_serial,
        ballots=((("a",), 1), (("b",), 1), (("c",), 1)),
        winners=2,
        quota_method=droop_quota,
    )
    assert not result.complete


def test_all_wins():
    from stvpoll.base import calculate_stv
    from stvpoll.transfer_strategies import transfer_serial
    from stvpoll.quotas import droop_quota

    ballots = [(("a", "b"), 2), (("b", "c"), 1)]
    result = calculate_stv(
        candidates=("a", "b", "c"),
        ballots=ballots,
        tiebreak_strategies=(),
        transfer_strategy=transfer_serial,
        winners=3,
        quota_method=droop_quota,
    )
    assert result.complete
    assert result.empty_ballot_count == 0
    assert result == ["a", "b", "c"]


def test_candidate_does_not_exist():
    poll = DummySTV(seats=2, candidates=["one", "two", "three"])
    with pytest.raises(CandidateDoesNotExist):
        poll.add_ballot(["a", "b"])


def test_counter_votes():
    from stvpoll.base import calculate_stv
    from stvpoll.transfer_strategies import transfer_serial
    from stvpoll.quotas import droop_quota

    votes = Counter([(), ("a", "b"), ("b", "c"), ("a", "b")])
    result = calculate_stv(
        candidates=("a", "b", "c"),
        ballots=votes,
        tiebreak_strategies=(),
        transfer_strategy=transfer_serial,
        winners=2,
        quota_method=droop_quota,
    )
    assert result.complete
    assert result.empty_ballot_count == 1
    assert result == ["a", "b"]
