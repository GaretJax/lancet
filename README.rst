======
LANCET
======

.. image:: https://badge.fury.io/py/lancet.png
    :target: http://badge.fury.io/py/lancet

.. image:: https://travis-ci.org/GaretJax/lancet.png?branch=master
        :target: https://travis-ci.org/GaretJax/lancet

.. image:: https://pypip.in/d/lancet/badge.png
        :target: https://crate.io/packages/lancet?version=latest


From http://en.wikipedia.org/wiki/Scalpel:

    A scalpel, or lancet, is a small and extremely sharp bladed instrument used
    for surgery, anatomical dissection, and various arts and crafts (called a
    hobby knife).

Lancet is a command line utility to streamline the various activities related
to the development and maintenance of a software package.

* Free software: MIT license
* Documentation: http://lancet.rtfd.org.


Install
-------

Not yet released on PyPI:

    brew install libgit2
    pipsi install --python=$(which python3) https://github.com/GaretJax/lancet/archive/master.zip


Features
--------

* Start tasks (create branch, set correct issue status/assignee, start linked harvest timer)
* Suspend tasks (pause harvest timer, set issue status)
* Resume tasks (resume timer, set issue status)
* Rapidly open issue tracker task page

See http://cl.ly/0u28140B1Y15 and ``lancet --help`` for additional details.
