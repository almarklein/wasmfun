"""
A Python library that provides tools to handle WASM code, like generating
WASM, and perhaps someday interpreting it too.
"""

__version__ = '0.1'

from ._opcodes import OPCODES
from .fields import *
from .util import *
