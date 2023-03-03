from __future__ import annotations

from collections import namedtuple
from typing import Generic, Optional, Type, TypeVar
from weakref import WeakSet

import js

from .. import env
from . import Component, TComponent, prop

T = TypeVar('T')

ROUTE_TREE_ITEM_KEY = object()
ROUTE_TREE_PARAM_KEY = object()

_router_registry: set[Router] = WeakSet()


class RouteTree(Generic[T]):
    MatchedPath = namedtuple('MatchedPath', ['item', 'params'])

    def __init__(self) -> None:
        self.root = {}
        self.paths = set()

    def insert(self, path: str, obj: T):
        current = self.root
        for segment in path.split('/'):
            if not segment:
                continue
            if segment[0] != ':':
                if segment not in current:
                    current[segment] = {}
                current: dict = current[segment]
            else:
                if ROUTE_TREE_PARAM_KEY not in current:
                    current[ROUTE_TREE_PARAM_KEY] = {}
                current: dict = current[ROUTE_TREE_PARAM_KEY]

        if ROUTE_TREE_ITEM_KEY in current and not env._is_reload_context:
            raise ValueError('Route path already defined')

        current[ROUTE_TREE_ITEM_KEY] = obj
        self.paths.add(path)

    def match(self, path: str) -> MatchedPath:
        current = self.root
        params = []
        for segment in path.split('/'):
            if not segment:
                continue
            if segment in current:
                current: dict = current[segment]
            else:
                if ROUTE_TREE_PARAM_KEY not in current:
                    return None
                current: dict = current[ROUTE_TREE_PARAM_KEY]
                params.append(segment)

        return self.MatchedPath(current.get(ROUTE_TREE_ITEM_KEY), tuple(params))

    def remove(self, path: str) -> T:
        current = self.root
        for segment in path.split('/'):
            if not segment:
                continue
            if segment[0] != ':':
                if segment not in current:
                    raise ValueError('Route path not found')
                current: dict = current[segment]
            else:
                if ROUTE_TREE_PARAM_KEY not in current:
                    raise ValueError('Route path not found')
                current: dict = current[ROUTE_TREE_PARAM_KEY]

        if ROUTE_TREE_ITEM_KEY not in current:
            raise ValueError('Route path not found')

        self.paths.remove(path)
        return current.pop(ROUTE_TREE_ITEM_KEY)


class Router(Component):
    root = prop()

    _component_cls: Optional[Type[TComponent]] = None
    _component_instance: TComponent

    def render(self):
        url_path: str = js.window.location.pathname
        matched = _route_tree.match(url_path)

        if matched.item is None:
            self._component_cls = None
            self._component_instance = None
            return f'Unmatched path {url_path}'

        if matched.item is not self._component_cls:
            self._component_cls = matched.item
            self._component_instance = self._component_cls()

        return self._component_instance

    def on_load(self):
        _router_registry.add(self)

    def on_unload(self):
        _router_registry.remove(self)


def route(path: str):
    if not isinstance(path, str):
        raise ValueError('Expected route path to be a string')

    def _d(component):
        assert issubclass(component, Component)
        _route_tree.insert(path, component)
        return component

    return _d


def navigate(path: str):
    import js
    js.window.history.pushState(None, None, path)
    for r in _router_registry:
        r._update()


_route_tree = RouteTree[Component]()
