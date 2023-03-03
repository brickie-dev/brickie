import multiprocessing
import os
import shutil
import subprocess

from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import build
import pytest
import tomli_w

from brickie.bundle import build_bundle, build_import_modules


@contextmanager
def chdir(path):
    old_cwd = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(old_cwd)


@pytest.fixture(scope='module')
def client_env(request: pytest.FixtureRequest):
    with TemporaryDirectory() as tmp:
        no_cache = request.config.getoption('no_cache')
        target_dir = request.config.getoption('cache_dir')
        if no_cache:
            target_dir = Path(tmp)
        else:
            target_dir = Path(target_dir).absolute()
            target_dir.mkdir(parents=True, exist_ok=True)

        (target_dir / 'client').mkdir(exist_ok=True, parents=True)
        (target_dir / 'generated').mkdir(exist_ok=True, parents=True)
        build.ProjectBuilder(os.getcwd()).build('wheel', target_dir / 'deps')

        pyproject = {
            'project': {},
            'tool': {
                'brickie': {
                    'npm_packages': [
                        'jsdom: 21.1.0',
                        '@mantine/core: 5.10.5',
                    ]
                }
            }
        }
        (target_dir / 'pyproject.toml').write_text(tomli_w.dumps(pyproject))
        (target_dir / 'generated/jsdom.mjs').write_text('''
            import { JSDOM } from "jsdom";
            const dom = new JSDOM(`<!DOCTYPE html><html><head></head><body></body></html>`);
            global.window = dom.window;
            global.document = dom.window.document;
            global.navigator = dom.window.navigator;
            window.console = global.console;
            export { dom };
        ''')

        with chdir(target_dir):
            build_import_modules(target_dir)
            yield target_dir


def test_client(client_env: Path, entry: Path, is_reload_enabled: bool):
    shutil.copy(entry, client_env / 'client/run.py')

    # Build bundle in new clean process
    mp = multiprocessing.get_context('spawn')
    p = mp.Process(target=build_bundle, args=(client_env, 'client.run'))
    p.start()
    p.join()

    install_deps = [
        f'await micropip.install("emfs:/local/deps/{dep.name}")'
        for dep in (Path(client_env) / 'deps').glob('*.whl')
    ]

    run = f'''
        import "./generated/jsdom.mjs";
        import "./generated/imports.mjs";
        import {{ loadPyodide }} from "pyodide/pyodide.js";

        let pyodide = await loadPyodide();
        await pyodide.loadPackage("micropip");

        pyodide.FS.mkdir("/local");
        pyodide.FS.mount(pyodide.FS.filesystems.NODEFS, {{ root: "{client_env}" }}, "/local");

        await pyodide.runPythonAsync(`
            import os
            os.chdir('/local')

            import micropip
            { ';'.join(install_deps) }

            import sys
            if '' not in sys.path:
                sys.path = [''] + sys.path

            from brickie import Component, env
            Component._allow_render_exceptions = True
            env.IS_RELOAD_ENABLED = {is_reload_enabled}

            from client.run import App
            app = App()
            app._create_root()
        `);
    '''
    (client_env / 'run.mjs').write_text(run)

    result = subprocess.run(['node', 'run.mjs'])
    assert result.returncode == 0


def pytest_generate_tests(metafunc: pytest.Metafunc):
    tests = Path(__file__).parent / 'tests'
    if metafunc.config.getoption('test_client'):
        metafunc.parametrize('entry', [
            pytest.param(p, id=str(p))
            for p in tests.glob('test_*.py')
        ])
        metafunc.parametrize('is_reload_enabled', [
            pytest.param(p, id=f'reload:{p}')
            for p in [False, True]
        ])
    else:
        metafunc.parametrize('entry', [])
