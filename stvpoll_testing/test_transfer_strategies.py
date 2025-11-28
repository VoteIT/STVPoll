from decimal import Decimal


def test_transfer_all():
    from stvpoll.transfer_strategies import transfer_all
    from stvpoll.abcs import PreferenceBallot

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
    assert transfers == {(1, 3): Decimal("2.4"), (2, 3): Decimal(0)}, (
        "transfer_quota: (5-2)/5=0.6, transfer value: 4*tq"
    )
    assert exhausted == Decimal(".6")
    assert votes == {3: Decimal("3.4")}
    assert ballots[0].multiplier == Decimal("0.6")
    assert ballots[1].multiplier == Decimal(0)


def test_transfer_serial():
    from stvpoll.transfer_strategies import transfer_serial
    from stvpoll.abcs import PreferenceBallot

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
    assert exhausted == Decimal(".6")
    assert transfers == {(1, 2): Decimal("2.400"), (2, 3): Decimal("2.398")}
    assert ballots[1].multiplier == Decimal("0.545"), "(4.4-2)/4.4 = 0.545"
    assert ballots[0].multiplier == Decimal("0.327"), "0.6*0.54545 = 0.327"
    assert votes == {3: Decimal("3.398")}
