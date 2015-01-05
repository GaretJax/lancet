=======================
Contribution guidelines
=======================


Creating a release
==================

* Checkout the ``master`` branch.
* Make sure ``check-manifest`` is happy.
* Pull the latest changes from ``origin``.
* Increment the version number.
* Set the correct title for the release in ``HISTORY.rst``.
* Commit everything and make sure the working tree is clean.
* Tag the release ``git tag -a "v$(python setup.py --version)" -m "$(python setup.py --name) release version $(python setup.py --version)"``.
* Build and upload the release ``python setup.py sdist bdist_wheel upload``.
* Push everything to github ``git push --tags origin master``.
