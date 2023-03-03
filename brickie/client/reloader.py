import importlib
import json
import sys

from pathlib import Path

import js

from pyodide.ffi import create_proxy

from .. import env
from .esm import _imports_cache
from .react import ReactReloadWrapperComponent


def init():
    env.IS_RELOAD_ENABLED = True

    # TODO: auto reconnect
    loc = js.window.location
    prot = 'wss:' if loc.protocol == 'https:' else 'ws:'
    uri = f'{prot}//{loc.host}/_dev/reloader'
    ws = js.WebSocket.new(uri)

    def on_open(event):
        print('Reloader WebSocket created ...')

    def on_message(event):
        event_data = json.loads(event.data)
        change_type = event_data['c']
        change_path = Path(event_data['p'])
        src = event_data['s']
        if change_type in (1, 2):
            if not change_path.exists():
                print(f'Added {change_path} ...')
            else:
                print(f'Updated {change_path} ...')
            with open(change_path, 'wt') as fp:
                fp.write(src)

            # Check if module is loaded and reload it
            modules = {
                Path(m.__file__): m
                for m in sys.modules.values()
                if getattr(m, '__file__', None)
            }
            loaded_module = modules.get(change_path.absolute())
            if not loaded_module:
                return

            with env._reload_context():
                reloaded_module = importlib.reload(loaded_module)

                # Find reload wrapper subclass for each component for reloaded module and reload
                wrapper_subclasses = ReactReloadWrapperComponent._subclass_registry.get(reloaded_module.__name__)
                for wrapper_cls in wrapper_subclasses.values():
                    wrapper_cls._reload(reloaded_module)

        elif change_type == 3:
            raise NotImplementedError
        else:
            raise RuntimeError('Unexpected change type')

    ws.addEventListener('open', create_proxy(on_open))
    ws.addEventListener('message', create_proxy(on_message))
    js.window._reloader_websocket = ws
