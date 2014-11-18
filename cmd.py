#!/usr/bin/python3
"""
Simple command stub to run the command line tools without even installing a
development version of the package.
"""

import sys
import os
sys.path.insert(0, os.getcwd())

from lancet.cli import main
main(prog_name='lancet')
