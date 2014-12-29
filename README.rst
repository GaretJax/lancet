======
LANCET
======

.. image:: https://badge.fury.io/py/lancet.png
   :target: http://badge.fury.io/py/lancet

.. image:: https://pypip.in/d/lancet/badge.png
   :target: https://crate.io/packages/lancet?version=latest
   
.. image:: https://travis-ci.org/GaretJax/lancet.png?branch=master
   :target: https://travis-ci.org/GaretJax/lancet

.. image:: https://readthedocs.org/projects/lancet/badge/?version=latest
   :target: http://lancet.readthedocs.org/en/latest/

From http://en.wikipedia.org/wiki/Scalpel:

    A scalpel, or lancet, is a small and extremely sharp bladed instrument used
    for surgery, anatomical dissection, and various arts and crafts (called a
    hobby knife).

Lancet is a command line utility to streamline the various activities related
to the development and maintenance of a software package.

* Free software: MIT license
* Documentation: http://lancet.rtfd.org


Installation
------------

You can install ``lancet`` from PyPI_. The suggested way to get it on your
system is by using pipsi_::

   brew install libgit2
   pipsi install --python=$(which python3) lancet

Please note that the development version of pipsi is currently needed to
support installing Python 3 packages (and yes, ``lancet`` only runs under
python3).

.. _PyPI: https://pypi.python.org/pypi/lancet
.. _pipsi: https://github.com/mitsuhiko/pipsi


Getting started
---------------

Once installed, set up the initial configuration by running::

   lancet setup

TODO: For each not-yet-configured project, you can then run::

   cd path/to/project
   lancet init

This creates a new project-level configuration file that can be shared across
different users (and thus commited to source control).

Features
--------

* Start tasks (create branch, set correct issue status/assignee, start
  linked harvest timer)
* Suspend tasks (pause harvest timer, set issue status)
* Resume tasks (resume timer, set issue status)
* Rapidly open issue tracker task page

See http://cl.ly/0u28140B1Y15 for a short visual demo and ``lancet --help``
for additional details::

   Usage: lancet [OPTIONS] COMMAND [ARGS]...

   Options:
    -h, --help  Show this message and exit.

   Commands:
    browse  Open the issue tracker page for the given...
    logout  Forget saved passwords for the web services.
    pause   Pause work on the current issue.
    resume  Resume work on the currently active issue.
    setup   Run a wizard to create the user-level...
    time    Start an Harvest timer for the given issue.
    workon  Start work on a given issue.

TODO
----

A lot of commands are still missing, as for example:

* ``init``: to setup the project-level configuration for any given project.
* ``pr``: to open a new pull-request and update the tracker accordingly.
* ``review``: to streamline the whole reviewing process (pulling, linting,\
  diffs,...).
* ``merge``: to help in getting a more strict merge process in place (and
  cleanup afterwards). Can include rebasing helpers.
* Other issue tracker/Harvest interaction utilities (``list``, ``search``,
  ``comment``, ...)
