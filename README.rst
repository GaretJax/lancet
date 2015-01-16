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

.. image:: https://requires.io/github/GaretJax/lancet/requirements.svg?branch=master
   :target: https://requires.io/github/GaretJax/lancet/requirements/?branch=master
   :alt: Requirements Status

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
