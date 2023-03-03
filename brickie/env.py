import sys

from contextlib import contextmanager

IS_CLIENT = '_pyodide_core' in sys.modules
IS_RELOAD_ENABLED = False

_is_reload_context = False
_is_init_context = False


@contextmanager
def _reload_context():
    global _is_reload_context
    try:
        _is_reload_context = True
        yield
    finally:
        _is_reload_context = False


@contextmanager
def _init_context():
    global _is_init_context
    try:
        _is_init_context = True
        yield
    finally:
        _is_init_context = False
