import inspect

from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from brickie import server
from brickie.bundle import build_client_source


@pytest.fixture
def endpoint_registry():
    from brickie import _endpoint_registry, _endpoint_keys
    _endpoint_registry.clear()
    _endpoint_keys.clear()
    return _endpoint_registry


@contextmanager
def temp_module(obj, whitespace=4):
    src, _ = inspect.getsourcelines(obj)
    src = ''.join(l[whitespace:] for l in src)
    with NamedTemporaryFile('wt') as f:
        f.write(src)
        f.flush()
        yield Path(f.name)


def test_server_endpoint_key(endpoint_registry):
    @server
    async def test_server_function():
        a = 5 * 2
        return a


    src = build_client_source(__name__, Path(__file__))

    assert len(endpoint_registry) == 1
    key = list(endpoint_registry.keys())[0]
    assert key in src


def test_server_endpoint_object_method_key(endpoint_registry):
    class A:
        @server
        async def test_server_method():
            a = 5 * 2
            return a

    src = build_client_source(__name__, Path(__file__))

    assert len(endpoint_registry) == 1
    key = list(endpoint_registry.keys())[0]
    assert key in src


def test_server_endpoint_key_with_comments(endpoint_registry):
    @server
    # test comment
    async def test_server_function():
        return 1
        # test comment
        # more comments

    src = build_client_source(__name__, Path(__file__))

    assert len(endpoint_registry) == 1
    key = list(endpoint_registry.keys())[0]
    assert key in src


def test_server_body_not_on_client():
    @server
    async def test_secret_function():
        secret = 'very_secret'
        return 'result'

    with temp_module(test_secret_function) as path:
        src = build_client_source(__name__, path)
        assert 'very_secret' not in src


def test_server_methods():
    @server
    async def test_server_function():
        pass

    def local_function():
        @server
        async def test_server_function():
            pass

    class TestClass:
        @server
        async def test_server_method():
            pass

    with temp_module(test_server_function) as path:
        src = build_client_source(__name__, path)
        assert 'is_method=False' in src

    with temp_module(local_function) as path:
        src = build_client_source(__name__, path)
        assert 'is_method=False' in src

    with temp_module(TestClass) as path:
        src = build_client_source(__name__, path)
        assert 'is_method=True' in src
