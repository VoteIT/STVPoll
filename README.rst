STVPoll README
==============

.. image:: https://travis-ci.org/VoteIT/STVPoll.svg?branch=master
    :target: https://travis-ci.org/VoteIT/STVPoll

Library to perform STV Poll calculations.
The package was created as part of the VoteIT project, specifically to handle larger
elections that was hard to count with Markus Schulzes STV method.

Typical usage would be primary elections or elections with many winners
from a pool of many candidates. The result will be proportional.


Fully supported:

* Scottish STV
* Instant-Runoff Voting (IRV)

Mostly working:

* CPO STV (Does not fail gracefully if too many outcomes)


Example
-------

Case from:
https://en.wikipedia.org/wiki/Single_transferable_vote


.. code-block:: python

    from stvpoll.scottish_stv import ScottishSTV

    example_ballots = (
        (['orange'], 4),
        (['pear', 'orange'], 2),
        (['chocolate', 'strawberry'], 8),
        (['chocolate', 'bonbon'], 4),
        (['strawberry'], 1),
        (['bonbon'], 1),
    )

    poll = ScottishSTV(seats=3, candidates=['orange', 'chocolate', 'pear', 'strawberry', 'bonbon'])
    for (candidates, count) in example_ballots:
        poll.add_ballot(candidates, count)

    result = poll.calculate()


This will return a ElectionResult object that contains the result and some useful metadata.
The elected attribute contains the elected candidates.

Candidates to the left have higher preference, so:
['pear', 'orange'] means 'pear' before 'orange' etc.
The number is how many of that kind of ballot there is.


.. code-block:: python

    result.elected_as_tuple()
    ('chocolate', 'orange', 'strawberry')


Code & Contributions
--------------------

You may fork the code at:
https://github.com/VoteIT/STVPoll

Please report any bugs there, or email info@voteit.se

