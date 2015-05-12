======
LANCET
======

.. image:: https://img.shields.io/travis/GaretJax/lancet.svg
   :target: https://travis-ci.org/GaretJax/lancet

.. image:: https://img.shields.io/pypi/v/lancet.svg
   :target: https://pypi.python.org/pypi/lancet

.. image:: https://img.shields.io/pypi/dm/lancet.svg
   :target: https://pypi.python.org/pypi/lancet

.. image:: https://img.shields.io/coveralls/GaretJax/lancet/develop.svg
   :target: https://coveralls.io/r/GaretJax/lancet?branch=develop

.. image:: https://img.shields.io/badge/docs-latest-brightgreen.svg
   :target: http://lancet.readthedocs.org/en/latest/

.. image:: https://img.shields.io/pypi/l/lancet.svg
   :target: https://github.com/GaretJax/lancet/blob/develop/LICENSE

.. image:: https://img.shields.io/requires/github/GaretJax/lancet.svg
   :target: https://requires.io/github/GaretJax/lancet/requirements/?branch=master

.. .. image:: https://img.shields.io/codeclimate/github/GaretJax/lancet.svg
..   :target: https://codeclimate.com/github/GaretJax/lancet

From http://en.wikipedia.org/wiki/Scalpel:

    A scalpel, or lancet, is a small and extremely sharp bladed instrument used
    for surgery, anatomical dissection, and various arts and crafts (called a
    hobby knife).

Lancet is a command line utility to streamline the various activities related
to the development and maintenance of a software package.

* Free software: MIT license
* Documentation: http://lancet.rtfd.org


Installation
============

Check out the documentation_.

.. _documentation: http://lancet.readthedocs.org/en/latest/installation/


Getting started
===============

Once installed, set up the initial configuration by running::

   lancet setup

For each not-yet-configured project, you can then run::

   cd path/to/project
   lancet init

This creates a new project-level configuration file that can be shared across
different users (and thus commited to source control).

Install dev version
===================

::

   ~/.local/venvs/lancet/bin/pip uninstall lancet
   ~/.local/venvs/lancet/bin/pip install https://github.com/GaretJax/lancet/archive/master.zip


TODO
====

A lot of commands are still missing, as for example:

* ``review``: to streamline the whole reviewing process (pulling, linting,\
  diffs,...).
* ``merge``: to help in getting a more strict merge process in place (and
  cleanup afterwards). Can include rebasing helpers.
* Other issue tracker/Harvest interaction utilities (``list``, ``search``,
  ``comment``, ...)
