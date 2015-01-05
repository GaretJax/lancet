=======================
Contribution guidelines
=======================


Creating a release
==================

* Increment the version number.
* Set the correct title for the release in ``HISTORY.rst``.
* Commit everything and make sure the working tree is clean.
* Tag the release ``git tag -a v0.X -m 'lancet release version 0.X'``.
* Build and upload the release ``python setup.py sdist bdist_wheel upload``.
* Push everything to github ``git push --tags origin master``.
