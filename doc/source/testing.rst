=======
Testing
=======

Unit testing
============

Unit testing currently uses an in-memory sqlite database. Since Deckhand's
primary function is to serve as the back-end storage for UCP, the majority
of unit tests perform actual database operations. Mocking is used sparingly
because Deckhand is a fairly insular application that lives at the bottom
of a very deep stack; Deckhand only communicates with Keystone and Barbican.
As such, validating database operations is paramount to correctly testing
Deckhand.

Functional testing
==================

Prerequisites
-------------
Deckhand requires Docker to run its functional tests. A basic installation
guide for Docker for Ubuntu can be found
`here <https://docs.docker.com/engine/installation/linux/docker-ce/ubuntu/>`_.

Overview
--------
Deckhand uses `gabbi <https://github.com/cdent/gabbi>`_ as its functional
testing framework. Functional tests can be executed via::

    $ tox -e functional

The command executes ``tools/functional-tests.sh`` which:

    1) Launches Postgresql inside a Docker container.
    2) Sets up a basic Deckhand configuration file that uses Postgresql
       in its ``oslo_db`` connection string.
    3) Sets up a custom policy file with very liberal permissions so that
       gabbi can talk to Deckhand without having to authenticate against
       Keystone and pass an admin token to Deckhand.
    4) Instantiates Deckhand via ``uwisgi``.
    5) Calls gabbi which runs a battery of functional tests.

At this time, there are no functional tests for policy enforcement
verification. Negative tests will be added at a later date to confirm that
a 403 Forbidden is raised for each endpoint that does policy enforcement
absent necessary permissions.
