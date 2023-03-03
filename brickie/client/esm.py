from __future__ import annotations

from collections import defaultdict, namedtuple
from typing import Optional, Union

import js

from pyodide.ffi import JsProxy

from .. import env

_static_imports_defs = defaultdict(set)
_imports_cache = {}


def import_module(module: str, features: Optional[list[str]] = None) -> Union[JsProxy, tuple[JsProxy]]:
    if not env.IS_CLIENT:
        if features is None:
            _static_imports_defs[module] = True
            return None
        else:
            if _static_imports_defs[module] is not True:
                _static_imports_defs[module].update(features)
            return [None] * len(features)

    if module not in _imports_cache:
        try:
           module_proxy = getattr(js.window.__import, module)
        except AttributeError:
            raise RuntimeError(f'Import module "{module}" not found')
        _imports_cache[module] = {'__proxy': module_proxy}

    if features is None:
        return _imports_cache[module]['__proxy']

    feature_proxies = []
    for f in features:
        if f not in _imports_cache[module]:
            _imports_cache[module][f] = getattr(_imports_cache[module]['__proxy'], f)
        feature_proxies.append(_imports_cache[module][f])

    module_type = namedtuple(f'Module', features)
    return module_type(*feature_proxies)
