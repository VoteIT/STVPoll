import os

from stvpoll.scottish_stv import ScottishSTV, calculate_scottish_stv

WARD_WINNERS = (
    {"Kevin  LANG", "Louise YOUNG", "Graham HUTCHISON", "Norrie WORK"},
    {"Graeme BRUCE", "Neil GARDINER", "Ricky HENDERSON", "Susan WEBBER"},
    {"Robert Christopher ALDRIDGE", "Claire BRIDGMAN", "Mark BROWN"},
    {"Eleanor BIRD", "Jim CAMPBELL", "Cammy DAY", "George GORDON"},
    {"Gavin BARRIE", "Max MITCHELL", "Hal OSLER", "Iain  WHYTE"},
    {"Scott DOUGLAS", "Gillian GLOYER", "Frank ROSS"},
    {"Denis DIXON", "Catherine FULLERTON", "Ashley GRACZYK", "Donald WILSON"},
    {"Scott ARTHUR", "Phil DOGGART", "Jason RUST"},
    {"Gavin CORBETT", "Andrew JOHNSTON", "David KEY"},
    {"Nick COOK", "Melanie MAIN", "Neil ROSS", "Mandy WATT"},
    {"Karen DORAN", "Claire MILLER", "Jo MOWAT", "Alasdair RANKIN"},
    {"Marion DONALDSON", "Amy MCNEESE-MECHAN", "Susan RAE", "Lewis RITCHIE"},
    {"Chas BOOTH", "Adam MCVEY", "Gordon John MUNRO"},
    {"Ian CAMPBELL", "Joan GRIFFITHS", "John MCLELLAN", "Alex STANIFORTH"},
    {"Steve BURGESS", "Alison DICKIE", "Ian PERRY", "Cameron ROSE"},
    {"Lezley Marion CAMERON", "Derek HOWIE", "Lesley MACINNES", "Stephanie SMITH"},
    {"KATE CAMPBELL", "MARY CAMPBELL", "Maureen CHILD", "Callum LAIDLAW"},
)


def iter_election_data():
    election_dir = "stvpoll_testing/scottish_election_data/"
    for f in os.listdir(election_dir):
        ballots = []
        candidates = []
        with open(election_dir + f) as edata:
            standing, winners = map(int, edata.readline().strip().split(" "))
            while True:
                line = edata.readline().strip().split(" ")
                if line[0] == "0":
                    break
                count = int(line.pop(0))
                line.pop()
                ballots.append((map(int, line), count))
            for i in range(standing):
                candidates.append(edata.readline().strip()[1:-1])
        yield (
            int(f.split("_")[1]),
            tuple(candidates),
            (([candidates[i - 1] for i in b[0]], b[1]) for b in ballots),
            winners,
        )


def test_all():
    """
    Tests using data from real scottish elections.
    """
    for ward_number, candidates, ballots, winners in iter_election_data():
        poll = ScottishSTV(winners, candidates)
        for b in ballots:
            poll.add_ballot(*b)
        result = poll.calculate()
        assert result.elected_as_set() == WARD_WINNERS[ward_number - 1]


def test_all_func():
    """
    Tests using data from real scottish elections, using functional version.
    """
    for ward_number, candidates, ballots, winners in iter_election_data():
        result = calculate_scottish_stv(candidates, ballots, winners)
        assert result.elected_as_set() == WARD_WINNERS[ward_number - 1]
