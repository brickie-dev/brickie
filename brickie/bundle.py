from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
import urllib.parse

from collections import defaultdict
from pathlib import Path
from typing import Union
from zipfile import ZipFile

import build
import pkg_resources
import tomli

from . import env
from .client import html as H

DEFAULT_CLIENT_NPM_PACKAGES = {
    'react': '18.2.0',
    'react-dom': '18.2.0',
}

DEFAULT_BUILD_NPM_PACKAGES = {
    **DEFAULT_CLIENT_NPM_PACKAGES,
    'pyodide': '0.22.1',
    'esbuild': '0.17.8',
}


class ClientNodeTransformer(ast.NodeTransformer):
    def __init__(self, module_name: str, module_path: Path, src: str) -> None:
        super().__init__()
        self.module_name = module_name
        self.module_path = module_path
        self.src = src
        self.qualname_stack = []

    def visit_decorated(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]):
        for i, d in enumerate(node.decorator_list):
            if isinstance(d, ast.Name) and d.id == 'server':
                # Classes are removed completely
                if isinstance(node, ast.ClassDef):
                    return None

                # Only async supported for now
                if isinstance(node, ast.FunctionDef):
                    raise RuntimeError('Only async server functions supported')

                # Insert server decorator key into tree
                src = ast.get_source_segment(self.src, node).strip()
                qual_name = '.'.join(self.qualname_stack + [node.name])
                unique_id = f'{self.module_name}|{qual_name}|{src}'
                key = hashlib.sha256(unique_id.encode('utf-8')).hexdigest()
                node.decorator_list[i] = ast.Call(
                    func=ast.Name(id='server'),
                    args=[ast.Constant(key)],
                    keywords=[
                        ast.keyword('is_method', ast.Constant(
                            bool(self.qualname_stack and '<locals>' not in self.qualname_stack[-1]))
                        ),
                    ],
                )
                node.body = [ast.Pass()]
                break

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.visit_decorated(node)
        self.qualname_stack.append(f'{node.name}.<locals>')
        node = self.generic_visit(node)
        self.qualname_stack.pop()
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_decorated(node)
        self.qualname_stack.append(f'{node.name}.<locals>')
        node = self.generic_visit(node)
        self.qualname_stack.pop()
        return node

    def visit_ClassDef(self, node: ast.ClassDef):
        self.visit_decorated(node)
        self.qualname_stack.append(node.name)
        node = self.generic_visit(node)
        self.qualname_stack.pop()
        return node

    def visit_Assign(self, node: ast.Assign):
        # TODO: WIP, need to implement on server
        # Source transformer for
        # A, B = import_module('module') => A, B = import_module('module', ['A', 'B'])
        if not (
            # Only consider first target
            isinstance(node.targets[0], ast.Tuple) and

            # Assigned value must be a import_module call
            isinstance(node.value, ast.Call) and
            isinstance(node.value.func, ast.Name) and
            node.value.func.id == 'import_module' and

            # No features defined
            len(node.value.args) == 1
        ):
            return self.generic_visit(node)

        features = [ast.Constant(n.id) for n in node.targets[0].elts]
        node.value.args.append(ast.List(features))
        return self.generic_visit(node)


def get_config(section='tool.brickie'):
    with open('pyproject.toml', 'rb') as fp:
        config = tomli.load(fp)
    if 'tool' not in config or 'brickie' not in config['tool']:
        raise RuntimeError('No `tool.brickie` section found')

    if 'client_directories' not in config['tool']['brickie']:
        config['tool']['brickie']['client_directories'] = ['client']
    if 'npm_packages' not in config['tool']['brickie']:
        config['tool']['brickie']['npm_packages'] = ()
    if 'umd_packages' not in config['tool']['brickie']:
        config['tool']['brickie']['umd_packages'] = ()
    if 'styles' not in config['tool']['brickie']:
        config['tool']['brickie']['styles'] = ()

    keys = list(section.split('.'))
    while keys:
        config = config[keys.pop(0)]
    return config


def parse_npm_package_config(packages, defaults):
    pkg_config = {
        p[0].strip(): p[1].strip() if len(p) > 1 else 'latest'
        for p in [p.split(':') for p in packages]
    }

    # Add default client npm packages if not defined
    for pkg in defaults:
        if pkg in pkg_config:
            continue
        pkg_config[pkg] = defaults[pkg]
    return pkg_config


def generate_pyodide_entry(use_cdn=False) -> list[str]:
    assert not use_cdn
    return [
        'import * as __import_pyodide from "pyodide"',
        'window.__pyodideModule = __import_pyodide',
    ]


def generate_imports_entry(use_cdn=False) -> list[str]:
    from .client import esm

    config = get_config()
    pkg_config = parse_npm_package_config(config['npm_packages'], DEFAULT_CLIENT_NPM_PACKAGES)

    if use_cdn:
        import_from = 'https://cdn.jsdelivr.net/npm/{package_name}@{package_version}{package_path}/+esm'
    else:
        import_from = '{package_name}{package_path}'

    if env.IS_RELOAD_ENABLED:
        # If reload is enabled (dev), import all packages defined in config
        import_defs = {m: True  for m in pkg_config} | {m: True for m in esm._static_imports_defs}
    else:
        import_defs = esm._static_imports_defs

    imports = ['window.__import = {}']
    for import_module, import_features in import_defs.items():
        if import_module[0] == '@':
            import_scope, import_package, *import_path = import_module.split('/')
            import_package = f'{import_scope}/{import_package}'
        else:
            import_package, *import_path = import_module.split('/')

        if import_package not in pkg_config:
            raise RuntimeError(f'Import module "{import_package}" not defined in project packages')

        import_path = '/'.join([''] + import_path)
        import_hash = hashlib.sha256(import_module.encode('utf-8')).hexdigest()
        import_location = import_from.format(
            package_name=import_package,
            package_version=pkg_config[import_package],
            package_path=import_path)

        if import_features is True:
            imports.extend([
                f'import * as __import_{import_hash} from "{import_location}"',
                f'window.__import["{import_module}"] = __import_{import_hash}',
            ])
        else:
            import_aliased = ','.join(f'{f} as __import_{import_hash}_{f}' for f in import_features)
            import_object = ','.join(f'{f}: __import_{import_hash}_{f}' for f in import_features)
            imports.extend([
                f'import {{ {import_aliased} }} from "{import_location}"',
                f'window.__import["{import_module}"] = {{ {import_object} }}',
            ])

    return imports


def build_package_json(target_dir):
    config = get_config()
    pkg_config = parse_npm_package_config(config['npm_packages'], DEFAULT_BUILD_NPM_PACKAGES)
    out = {
        'name': 'brickie-bundle',
        'version': '0.0.1',
        'dependencies': pkg_config,
    }
    (Path(target_dir) / 'package.json').write_text(json.dumps(out))


def build_import_modules(target_dir):
    target_dir = Path(target_dir)

    build_package_json(target_dir)
    subprocess.run(['npm', 'install'], cwd=target_dir)

    gen_dir = target_dir / 'generated'
    gen_dir.mkdir(exist_ok=True)
    (gen_dir / 'imports.mjs').write_text(';'.join(generate_imports_entry()))
    (gen_dir / 'pyodide.mjs').write_text(';'.join(generate_pyodide_entry()))
    subprocess.run([
        'npx',
        'esbuild',
        'generated/imports.mjs',
        'generated/pyodide.mjs',
        '--format=esm',
        '--bundle',
        '--outdir=./bundle',
    ], cwd=target_dir)


def build_client_source(module_name: str, module_path: Path) -> str:
    src = module_path.read_text()
    ast_node = compile(
        source=src,
        filename=module_path,
        mode='exec',
        flags=ast.PyCF_ONLY_AST,
    )
    ast_node = ClientNodeTransformer(module_name, module_path, src).visit(ast_node)
    return ast.unparse(ast_node)


def build_bundle(target_dir: Path, entry_module: str):
    # Add working directory to path
    if '' not in sys.path:
        sys.path = [''] + sys.path
    __import__(entry_module)

    files: dict[str, Path] = defaultdict(list)
    from .client import react
    react.build_bundle(files)

    config = get_config()
    cwd = Path('.').absolute()
    client_dirs = [cwd / d for d in config['client_directories']]

    with ZipFile(target_dir / 'dist.zip', 'w') as zf:
        # Build transformed client bundle from client directories
        for module_name, module_path in files.items():
            if not any(module_path.is_relative_to(d) for d in client_dirs):
                raise RuntimeError('Component found outside client directories')
            src = build_client_source(module_name, module_path)
            rel_module_path = module_path.relative_to(cwd)
            zf.writestr(str(rel_module_path), src)

        # Build stubs for everything outside client directories
        from . import _endpoint_keys, _endpoint_registry
        for module_path in _endpoint_keys:
            if any(module_path.is_relative_to(d) for d in client_dirs):
                continue
            src = ['from brickie import server']
            for endpoint_key in _endpoint_keys[module_path.absolute()]:
                endpoint_name = _endpoint_registry[endpoint_key].__name__
                src.extend([
                    f'@server("{endpoint_key}", is_method=False)',
                    f'def {endpoint_name}(*args, **kwargs): ...'
                ])
            src = '\n'.join(src)
            rel_module_path = module_path.relative_to(cwd)
            zf.writestr(str(rel_module_path), src)


def build_index(target_dir, dependencies=(), options=None) -> H.Tag:
    config = get_config()
    entry_module, entry_component = config['entry'].split(':')
    build_bundle(target_dir, entry_module)
    if options.get('build_import_modules', True):
        build_import_modules(target_dir)

    install_deps = [f'await micropip.install("{dep}")' for dep in dependencies]
    return H.html(
        H.head(
            H.style (
                (Path(__file__).parent / 'assets' / 'spinner.css').read_text()
            ),
            *(H.script(src=url) for url in config['umd_packages']),
            *(H.link(href=url, rel='stylesheet') for url in config['styles']),
        ),
        H.body(
            H.div(_class='__loading-modal') (
                H.div(_class='__loading-spinner'),
            ),
            H.script(type='module') (f'''
                async function load() {{
                    let distPromise = fetch('_s/dist.zip');

                    async function installPackages() {{
                        let pyodide = await window.__pyodidePromise;
                        await pyodide.loadPackage('micropip');
                        await pyodide.runPythonAsync(`
                            import micropip
                            {';'.join(install_deps)}
                        `);
                    }}

                    async function unpackDist(){{
                        let dist = await (await distPromise).arrayBuffer();
                        let pyodide = await window.__pyodidePromise;
                        await pyodide.unpackArchive(dist, 'zip');
                    }}

                    await Promise.all([
                        installPackages(),
                        unpackDist(),
                    ]);
                }}
                window.__pyodidePromise = loadPyodide();
                window.__loadPromise = load();
            '''),
            H.script(type='module', src='_s/bundle/imports.js'),
            H.script(type='module') (f'''
                let pyodide = await window.__pyodidePromise;
                await window.__loadPromise;
                await pyodide.runPythonAsync(`
                    {
                        'from brickie.client.reloader import init; init()'
                        if options and options.get('reload')
                        else ''
                    }
                    from {entry_module} import {entry_component}
                    {entry_component}()._create_root()
                `);
                document.getElementsByClassName('__loading-modal')[0].style.visibility = 'hidden';
            '''),
        ),
    )


def build_deps(target_dir) -> list[str]:
    config = get_config('project')

    target_dir = Path(target_dir)
    target_dir.mkdir(exist_ok=True, parents=True)

    deps = {
        p.key: p
        for p in pkg_resources.parse_requirements(config.get('client_dependencies', ()))
    }
    if 'brickie' not in deps:
        brickie_version = pkg_resources.get_distribution('brickie').version
        deps['brickie'] = pkg_resources.Requirement.parse(f'brickie=={brickie_version}')

    out = []
    for dep in deps.values():
        for info in pkg_resources.working_set:
            if dep.project_name != info.key:
                continue

            # Check if editable install and package that instead
            link = Path(info.egg_info) / 'direct_url.json'
            if not link.exists():
                continue
            with open(link, 'rt') as fp:
                link = json.load(fp)
            if not link['dir_info']['editable']:
                continue
            path = urllib.parse.urlparse(link['url']).path
            build_path = build.ProjectBuilder(path).build('wheel', target_dir)
            out.append(f'_s/deps/{Path(build_path).name}')
            break
        else:
            out.append(dep.project_name)

    return out


def build_runtime(target_dir='.brickie/build', options=None):
    options = options or {}
    target_dir = Path(target_dir)
    target_dir.mkdir(exist_ok=True, parents=True)

    deps = build_deps(target_dir=target_dir / 'deps')
    with open(target_dir / 'index.html', 'wt') as fp:
        index = build_index(target_dir, dependencies=deps, options=options).to_html()
        out = '<!DOCTYPE html>' + index
        fp.write(out)
