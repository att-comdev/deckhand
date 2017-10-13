========
Deckhand
========

Deckhand is a document-based configuration storage service built with
auditability and validation in mind.

Essential Functionality
=======================

* layering - helps reduce duplication in configuration while maintaining
  auditability across many sites
* substitution - provides separation between secret data and other
  configuration data, while allowing a simple interface for clients
* revision history - improves auditability and enables services to provide
  functional validation of a well-defined collection of documents that are
  meant to operate together
* validation - allows services to implement and register different kinds of
  validations and report errors

Getting Started
===============

To generate a configuration file automatically::

	$ tox -e genconfig

Resulting deckhand.conf.sample file is output to
:path:etc/deckhand/deckhand.conf.sample

Copy the config file to a directory discoverably by ``oslo.conf``::

	$ cp etc/deckhand/deckhand.conf.sample ~/deckhand.conf

To setup an in-memory database for testing:

.. code-block:: ini

	[database]

	#
	# From oslo.db
	#

	# The SQLAlchemy connection string to use to connect to the database.
	# (string value)
	connection = sqlite:///:memory:

To run locally in a development environment::

	$ sudo pip install uwsgi
	$ virtualenv -p python3 /var/tmp/deckhand
	$ . /var/tmp/deckhand/bin/activate
	$ sudo pip install .
	$ sudo python setup.py install
	$ uwsgi --http :9000 -w deckhand.cmd --callable deckhand_callable --enable-threads -L
