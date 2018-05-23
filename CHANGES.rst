Changes
=======


0.2.0 (dev)
-----------

- Fixed bug in deciding which vote to transfer first when multiple elected in Scottish STV. [schyffel] [robinharms]
- Scottish STV: Resolve ties so that winners are always in correct ranking order (extreme case). [schyffel]
- Now works on Python 3. [schyffel]
- Test coverage 100 %. [schyffel]


0.1.4 (2018-05-12)
------------------

- Fixed a situation where primary_candidate in rounds didn't exist. [schyffel] [robinharms]


0.1.3 (2018-03-22)
------------------

- Excluded empty ballots, so that they do not affect the quota. [schyffel]


0.1.2 (2017-11-24)
------------------

- Fixed exception on empty ballots. [schyffel]


0.1.1 (2017-11-24)
------------------

- Fixed case where randomization caused an exception. [schyffel]


0.1.0 (2017-11-03)
------------------

-  Initial version
