"""
Configuration management for the different components.
"""

import os
import configparser
import importlib


PACKAGE = 'lancet'
LOCAL_CONFIG = '.{}'.format(PACKAGE)
DEFAULT_CONFIG = os.path.join(os.path.dirname(__file__),
                              'default-settings.ini')
SYSTEM_CONFIG = '/etc/{0}/{0}.conf'.format(PACKAGE)
USER_CONFIG = os.path.expanduser(os.path.join('~', LOCAL_CONFIG))
PROJECT_CONFIG = os.path.join(os.path.realpath('.'), LOCAL_CONFIG)

DEFAULT_FILES = [
    DEFAULT_CONFIG,
    SYSTEM_CONFIG,
    USER_CONFIG,
]


class ConfigParser(configparser.ConfigParser):
    def getclass(self, section, key):
        import_path = self.get(section, key)
        module_path, callable_name = import_path.rsplit('.', 1)
        return getattr(importlib.import_module(module_path), callable_name)

    def getlist(self, section, key, coerce=str):
        value = self.get(section, key)
        return [coerce(v.strip()) for v in value.splitlines() if v.strip()]


def load_config(path=None, defaults=None):
    """
    Loads and parses an INI style configuration file using Python's built-in
    configparser module. If path is specified, load it.
    If ``defaults`` (a list of strings) is given, try to load each entry as a
    file, without throwing any error if the operation fails.
    If ``defaults`` is not given, the following locations listed in the
    DEFAULT_FILES constant are tried.
    To completely disable defaults loading, pass in an empty list or ``False``.
    Returns the SafeConfigParser instance used to load and parse the files.
    """

    if defaults is None:
        defaults = DEFAULT_FILES

    config = ConfigParser(allow_no_value=True)

    if defaults:
        config.read(defaults)

    if path:
        with open(path) as fh:
            config.read_file(fh)

    return config
