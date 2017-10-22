class STVException(Exception):
    pass


class IncompleteResult(STVException):
    pass


class BallotException(STVException):
    pass


class CandidateDoesNotExist(BallotException):
    pass
