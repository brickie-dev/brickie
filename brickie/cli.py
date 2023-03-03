from pathlib import Path

import click

from . import bundle, env


@click.group()
def cli():
    pass


@cli.command()
def build():
    bundle.build_runtime()


@cli.command()
@click.option('--host', default='127.0.0.1', help='Bind server to this host')
@click.option('--port', default=5000, type=int, help='Bind server to this port')
@click.option('--reload', default=False, is_flag=True, help='Enable auto-reload')
def serve(host: str, port: int, reload: bool):
    import uvicorn

    from starlette.applications import Starlette
    from starlette.staticfiles import StaticFiles

    from . import _endpoint_registry
    from .client.router import _route_tree
    from .serve import create_endpoint, index

    app = Starlette()

    if reload:
        from . import dev
        env.IS_RELOAD_ENABLED = True
        dev.watch_for_reload(app, Path('.'))

    bundle.build_runtime(options={
        'reload': reload,
    })

    # Redirect client routes to index
    for p in _route_tree.paths:
        app.add_route(p, index)
    app.add_route('/', index)

    for key, endpoint in _endpoint_registry.items():
        app.add_route(
            name=key,
            path=f'/_c/{key}',
            route=create_endpoint(endpoint),
            methods=['POST'])

    app.mount('/_s', StaticFiles(directory=Path('.brickie/build'), html=True))
    uvicorn.run(app, host=host, port=port, log_level='info')
