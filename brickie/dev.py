import importlib
import inspect
import sys
import traceback

from asyncio import Queue
from collections import defaultdict
from pathlib import Path
from threading import Thread
from weakref import WeakKeyDictionary

import websockets.exceptions

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.websockets import WebSocket
from watchfiles import Change, DefaultFilter, watch

from . import _endpoint_keys, _endpoint_registry, env
from .bundle import build_client_source, build_runtime, get_config
from .serve import create_endpoint


def watch_for_reload(app: Starlette, root_path: Path):
    change_queues: dict[WebSocket, Queue] = WeakKeyDictionary()

    # module path -> set(route key)
    module_keys: dict[Path, set[str]] = defaultdict(set)
    for key, endpoint in _endpoint_registry.items():
        path = Path(inspect.getfile(endpoint))
        module_keys[path].add(key)

    def watch_thread():
        ignore_dirs = DefaultFilter.ignore_dirs + ('.brickie', )
        watch_filter = DefaultFilter(ignore_dirs=ignore_dirs)
        current_packages = get_config()['npm_packages']

        for changes in watch(root_path, watch_filter=watch_filter, recursive=True):
            try:
                build_runtime(options={
                    'reload': True,
                    'build_import_modules': False,
                })
            except Exception as exc:
                traceback.print_exception(exc)
                continue

            for change in changes:
                modules = {
                    Path(m.__file__): m
                    for m in sys.modules.values()
                    if getattr(m, '__file__', None)
                }
                change_type, change_path = change
                change_path = Path(change_path)

                # If packages changes, full reload page
                if change_path.name == 'pyproject.toml':
                    new_packages = get_config()['npm_packages']
                    if current_packages != new_packages:
                        # TODO: full reload page
                        print('Packages changed, full reload')
                        build_runtime(options={
                            'reload': True,
                            'build_import_modules': True,
                        })
                        current_packages = new_packages
                        continue

                if change_path.suffix != '.py':
                    continue

                # Get current route keys to be delete
                # And clear endpoint registry for changed module
                if change_type in (Change.modified, Change.deleted):
                    to_delete_keys = set(module_keys[change_path])
                    for key in to_delete_keys:
                        _endpoint_registry.pop(key, None)
                    _endpoint_keys[Path(change_path).absolute()].clear()
                else:
                    to_delete_keys = set()

                # Reload module
                loaded_module = modules.get(change_path)
                if not loaded_module:
                    continue
                with env._reload_context():
                    try:
                        importlib.reload(loaded_module)
                    except Exception as exc:
                        traceback.print_exception(exc)
                        continue

                # Add new routes
                module_keys[change_path] = set()
                routes = {r.name: r for r in app.routes if isinstance(r, Route)}
                for key, endpoint in _endpoint_registry.items():
                    path = Path(inspect.getfile(endpoint))
                    if path != change_path:
                        continue

                    assert key not in module_keys[path]
                    module_keys[path].add(key)
                    to_delete_keys.discard(key)

                    if key in routes:
                        routes[key].endpoint = create_endpoint(endpoint)
                    else:
                        app.router.routes.insert(0, Route(
                            name=key,
                            path=f'/_c/{key}',
                            endpoint=create_endpoint(endpoint),
                            methods=['POST']))

                # Rebuild src
                src = build_client_source(loaded_module.__name__, change_path)

                # Notify all clients
                for queue in change_queues.values():
                    queue.put_nowait((change_type, change_path, src))

                # Delete old routes
                app.router.routes = [r for r in app.routes if r.name not in to_delete_keys]


    async def client_reloader(ws: WebSocket):
        try:
            await ws.accept()
            change_queues[ws] = Queue()
            while True:
                change_type, change_path, src = await change_queues[ws].get()
                change_path = Path(change_path)
                change_path = change_path.relative_to(root_path.absolute())
                await ws.send_json({
                    'c': change_type,
                    'p': str(change_path),
                    's': src,
                })
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            del change_queues[ws]
            await ws.close()

    app.add_websocket_route('/_dev/reloader', client_reloader)
    Thread(target=watch_thread, daemon=True).start()
