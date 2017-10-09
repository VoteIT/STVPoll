class STVException(Exception):
    pass

class ResolveTieError(STVException):
    pass

class BallotException(STVException):
    pass

class CandidateDoesNotExist(BallotException):
    pass
