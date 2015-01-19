=======
History
=======

0.6.0 - 2015-01-19
==================

* Added support for pluggable Harvest task/project mapper.
* Added support for epics based time tracking.
* Added support for pluggable branch naming backends.
* Added support for different branch prefixes based on issue type.
* Added URL hints to ``lancet setup``.
* Fix assignee comparison bug.
* More robust support for flawed versions of the git ``osxkeychain``
  credentials helper.
* Increase the slug length in branch names to 50 chars.
* Built in support for debugging exceptions.


0.5.1 - 2015-01-13
==================

* Coerce config values to int when calling `init`.


0.5.0 – 2015-01-05
==================

* Include all resources in the distribution.
* Cleanup docker-related leftovers.
* Added a ``pr`` command to automate pull requests creation.
* The ``logout`` command can now logout from a single service.

0.4.2 – 2015-01-05
==================

* Fix ``python-slugify`` requirement.


0.4.1 – 2015-01-05
==================

* Update requirements.


0.4 – 2015-01-05
================

.. warning::

   If your setup includes remote configured to be accessed over SSH, you may
   need to reinstall ``libgit2`` with ``brew reinstall libgit2 --with-libssh2``.

* Added facilities to integrate with the current shell, for stuff like cd'ing
  to other directories or activating virtual environments.
* Added a ``--version`` option to ``lancet``.
* Fetch latest changes from origin before creating new working branches (#1).
* Added an ``activate`` command to ``cd`` to the project directory and
  (optionally) activate a virtual environment.
* Added the ``harvest-projects`` and ``harvest-tasks`` commands to list
  projects/tasks IDs from Harvest.
* Added an ``init`` command to create project-level configuration files (#2).


0.3 – 2014-12-30
================

* Handle unassigned issues (#5).
* Avoid logging out the web user when accessign the JIRA API (#4).
* Initial documentation stub (#3).
