=======
History
=======

Unreleased
==========

.. warning::

   If your setup includes remote configured to be accessed over SSH, you may
   need to reinstall ``libgit2`` with ``brew reinstall libgit2 --with-libssh2``.

* Added facilities to integrate with the current shell, for stuff like cd'ing
  to other directories or activating virtual environments.
* Added a ``--version`` option to ``lancet``.
* Fetch latest changes from origin before creating new working branches (#1).
* Added an ``activate`` command to ``cd`` to the project directory and
  (optionally) activate a virtual environment.

0.3 - 2014-12-30
================

* Handle unassigned issues (#5).
* Avoid logging out the web user when accessign the JIRA API (#4).
* Initial documentation stub (#3).
