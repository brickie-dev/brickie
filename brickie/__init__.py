from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Callable
from weakref import WeakValueDictionary

from .client import html
from .client.react import Component, ReactImportModule, prop, state
from .client.style import Style

_endpoint_registry: dict[str, Callable] = WeakValueDictionary()
_endpoint_keys: dict[Path, set] = defaultdict(set)


def server(f, is_method=False):
    from . import env

    if not env.IS_CLIENT:
        if isinstance(f, type):
            return f

        import hashlib
        import inspect
        import tokenize
        module = inspect.getmodule(f)
        module_name = module.__name__

        # Ignore trailing comments as AST does not retain them
        lines, lnum = inspect.findsource(f)
        lines = inspect.getblock(lines[lnum:])
        tokens = tokenize.generate_tokens(iter(lines).__next__)
        block_finder = inspect.BlockFinder()
        try:
            for t in tokens:
                if t.type is tokenize.COMMENT:
                    continue
                block_finder.tokeneater(*t)
        except (inspect.EndOfBlock, IndentationError):
            pass

        src = ''.join(lines[:block_finder.last])
        src = 'async def ' + src.split('async def ', 1)[-1].strip()

        unique_id = f'{module_name}|{f.__qualname__}|{src}'
        key = hashlib.sha256(unique_id.encode('utf-8')).hexdigest()
        if key in _endpoint_registry and not env._is_reload_context:
            raise RuntimeError('Server key collision')
        _endpoint_registry[key] = f
        _endpoint_keys[Path(module.__file__).absolute()].add(key)
        return f

    # Check server decorator transformed by ast transformer
    if not isinstance(f, str):
        raise RuntimeError('Server code running on client')
    assert isinstance(f, str)

    import json

    from functools import wraps

    import pyodide

    server_key = f

    def _d(f):
        @wraps(f)
        async def _wrapper(*args, **kwargs):
            print('Calling', server_key)

            # Strip away `self`
            if is_method:
                args = args[1:]

            result = await pyodide.http.pyfetch(f'/_c/{server_key}',
                method='POST',
                body=json.dumps({'a': args, 'k': kwargs})
            )
            result_json = await result.json()
            return result_json['r']

        return _wrapper

    return _d
