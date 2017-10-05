from decimal import Decimal

from math import floor


class BallotException(Exception):
    pass


def droop_quota(poll):
    return int(floor((Decimal(poll.ballot_count) / (poll.seats +1 )) + 1))

def hare_quota(poll):
    return int(floor(Decimal(poll.ballot_count) / poll.seats))


class STVPollBase(object):
    quota = None
    candidates = ()
    seats = 0

    def __init__(self, quota = droop_quota, seats = 0, candidates = ()):
        self.candidates = tuple(candidates)
        self.ballots = {}
        self.quota = quota
        self.seats = seats

    @property
    def ballot_count(self):
        return sum([x for x in self.ballots.values()])

    def add_ballot(self, ballot, num=1):
        ballot = tuple(ballot)
        try:
            self.ballots[ballot] += num
        except KeyError:
            self.ballots[ballot] = num

    def verify_ballot(self, ballot):
        if len(set(ballot)) != len(ballot):
            raise BallotException("Duplicate candidates on ballot")
        for k in ballot:
            if k not in self.candidates:
                raise BallotException("%s is not in the list of candidates" % k)

    def calculate(self):
        raise NotImplementedError()


class ScottishSTV(STVPollBase):

    def calculate(self):
        pass
