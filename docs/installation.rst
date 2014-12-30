============
Installation
============


Requirements
============

The following carefully crafted software packages are needed to install
``lancet``:

1. Python 3 (``brew install python3``)
2. libgit2 (``brew install libgit2``)
3. pipsi (optional, see below)

Required `Python packages`_ are automatically installed.

.. _python packages: https://github.com/GaretJax/lancet/blob/master/requirements


``pipsi``-dev
=============

It is suggested to use ``pipsi`` to install ``lancet`` for production use.
``pipsi`` creates and manages isolated virtual environments for specific
Python packages, and then exposes the provided binaries in the global
``$PATH``.
For more information about ``pipsi``, please check out it's homepage_.

At the time of writing, the latest release of ``pipsi`` (0.8) does not support
Python 3. In order to install ``lancet``, we need to install the development
version of ``pipsi``. This can be achieved with the following commands:

1. Install the current stable release::

      curl https://raw.githubusercontent.com/mitsuhiko/pipsi/master/get-pipsi.py | python

2. Upgrade to the latest development release::

      ~/.local/venvs/pipsi/bin/pip install -U https://github.com/mitsuhiko/pipsi/archive/master.zip

.. _homepage: https://github.com/mitsuhiko/pipsi


Installation
============

``lancet`` can be installed as any other Python package (``pip``,
``easy_install``, ...), but it is recommended to use ``pipsi``.

If all the needed dependencies are installed on your system, and you have a
Python 3-compatible version of ``pipsi``, then installing is just a matter of
running the following command::

   pipsi install --python=$(which python3) lancet


Upgrading from a previous version
=================================

If you used ``pipsi`` to install ``lancet``, you can upgrade to the latest
version of ``lancet`` by running::

   pipsi upgrade lancet
