STVPoll README
==============

Library to perform STV Poll calculations.
The package was created as part of the VoteIT project, specifically to handle larger
elections that was hard to count with Markus Schulzes STV method.

Typical usage would be primary elections or elections with many winners
from a pool of many candidates. The result will be proportional.

Fully supported:

* Scottish STV
* Instant-Runoff Voting (IRV)

Mostly working:

* CPO STV (Do not use for polls with too many possible outcomes)

Python versions
---------------

Tested on python 3.10 through 3.13.

Example
-------

Case from:
https://en.wikipedia.org/wiki/Single_transferable_vote


.. code-block:: python

    from stvpoll.scottish_stv import calculate_scottish_stv

    candidates = ('orange', 'chocolate', 'pear', 'strawberry', 'bonbon')
    # votes can be collections.Counter, dict or list of tuples with candidates and vote count
    ballots = {
        ('orange'): 4,
        ('pear', 'orange'): 2,
        ('chocolate', 'strawberry'): 8,
        ('chocolate', 'bonbon'): 4,
        ('strawberry',): 1,
        ('bonbon',): 1,
    }

    result = calculate_scottish_stv(
        candidates=candidates,
        ballots=ballots,
        winners=3,
    )


This will return a ElectionResult object that contains the result and some useful metadata.

Each ballot is a list of candidates in order of preference, so: ['pear', 'orange'] means
'pear' before 'orange' etc.

Count is the number of ballots with those exact preferences. In the above example,
4 people voted for only 'orange', two people voted for 'pear' and then 'orange, and so on.

.. code-block:: python

    result.elected_as_tuple()
    ('chocolate', 'orange', 'strawberry')


Code & Contributions
--------------------

You may fork the code at:
https://github.com/VoteIT/STVPoll

Please report any bugs there, or email info@voteit.se
