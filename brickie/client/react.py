from __future__ import annotations

import asyncio
import inspect
import sys

from collections import defaultdict
from functools import partial
from pathlib import Path
from secrets import token_hex
from typing import Any, Callable, ClassVar, Optional, Type, TypeVar, Union, cast
from weakref import WeakSet

import js

from pyodide.ffi import JsProxy, create_proxy, to_js

from .. import env
from . import html
from .esm import import_module
from .style import Style

PROP_REQUIRED = object()

T = TypeVar('T')
TReactComponent = TypeVar('TReactComponent', bound='ReactComponent')

ReactJS = import_module('react')
ReactDOM = import_module('react-dom/client')


def to_js_obj(d: dict, *args, **kwargs):
    return to_js(d, dict_converter=js.Object.fromEntries, *args, **kwargs)


def to_camel_case(s: str):
    parts = str(s).split('_')
    return parts[0] + ''.join(p.title() for p in parts[1:])


def to_camel_case_attrs(a: dict):
    return {
        to_camel_case(key): value if value is not None else True
        for key, value in a.items()
    }


def to_react_element(obj: Union[html.Tag, ReactComponent, JsProxy, str]):
    if isinstance(obj, ReactComponent):
        if obj._class:
            obj._props['className'] = ' '.join(obj._class)
        render_props = {'_obj': create_proxy(obj, roundtrip=True)}
        render_props = to_js_obj(render_props, depth=1, create_pyproxies=False)
        return ReactJS.createElement(obj._render_proxy, render_props)
    elif isinstance(obj, (JsProxy, str)):
        return obj
    elif isinstance(obj, html.Tag):
        name = obj.__class__.__name__
        attrs = {}
        if obj._class:
            attrs['className'] = ' '.join(obj._class)
        attrs = to_js_obj({**to_camel_case_attrs(obj.attrs), **attrs})
        children = (
            to_react_element(c)
            for c in obj.children or ()
        )
        return ReactJS.createElement(name, attrs, *children)
    else:
        return str(obj)


def create_root(component: ReactComponent, element_id=None) -> JsProxy:
    if element_id is None:
        dom_container = js.document.createElement('div')
        js.document.body.appendChild(dom_container)
    else:
        dom_container = js.document.getElementById(element_id)

    root = ReactDOM.createRoot(dom_container)
    render_props = {'_obj': create_proxy(component, roundtrip=True)}
    render_props = to_js_obj(render_props, depth=1, create_pyproxies=False)
    root.render(ReactJS.createElement(component._render_proxy, render_props))
    return dom_container


def state(init_value: Union[T, Callable]) -> T:
    return cast(T, State(init_value))


def prop(default_value: Union[T, Callable] = PROP_REQUIRED) -> T:
    if default_value is PROP_REQUIRED:
        return cast(T, Prop(None, is_required=True))
    else:
        return cast(T, Prop(default_value, is_required=False))


def ref():
    return Ref()


def build_bundle(files: dict[str, Path]):
    for cls in ReactComponentMeta._component_registry:
        cls: type
        if cls.__module__.split('.')[0] == __name__.split('.')[0]:
            continue
        if cls.__module__ in files:
            continue
        files[cls.__module__] = Path(inspect.getfile(cls))


class State:
    def __init__(self, init_value):
        self.init_value = init_value


class Prop:
    def __init__(self, default_value, is_required):
        self.default_value = default_value
        self.is_required = is_required


class Ref:
    current: JsProxy

    def __init__(self):
        pass


class ReactComponentMeta(type):
    _component_registry = set()

    @staticmethod
    def create_state_accessor(name: str, init_value):
        tasks = set()

        def get_attr(self: TReactComponent):
            if name not in self._state_values:
                _init_value = init_value
                if callable(_init_value):
                    _init_value = _init_value()

                if inspect.isawaitable(_init_value):
                    async def get_init_value():
                        try:
                            val = await _init_value
                            self._state_values[name] = val
                            self._update()
                        finally:
                            tasks.remove(task)

                    task = asyncio.get_event_loop().create_task(get_init_value())
                    tasks.add(task)
                    self._state_values[name] = None
                else:
                    self._state_values[name] = _init_value
            return self._state_values[name]

        def set_attr(self: TReactComponent, value):
            self._state_values[name] = value
            self._update()

        return property(fget=get_attr, fset=set_attr)

    @staticmethod
    def create_prop_accessor(name: str, default_value):
        def get_attr(self: TReactComponent):
            if name not in self._props:
                _default_value = default_value
                if inspect.iscoroutinefunction(_default_value):
                    raise ValueError('Prop cannot be an async function')
                if callable(_default_value):
                    _default_value = _default_value()
                if inspect.isawaitable(_default_value):
                    raise ValueError('Prop cannot be an awaitable')
                self._props[name] = _default_value
            return self._props[name]

        return property(fget=get_attr)

    @staticmethod
    def create_ref_accessor(name: str):
        def get_attr(self: TReactComponent):
            if name not in self._refs:
                self._refs[name] = ReactJS.createRef()
            return self._refs[name]

        return property(fget=get_attr)

    def __new__(cls, name, bases, attrs):
        new_cls: Type[ReactComponent] = type.__new__(cls, name, bases, attrs)

        # Create class vars
        new_cls._props_defined = set()
        new_cls._props_required = set()

        # Create client proxies
        if env.IS_CLIENT:
            new_cls._render_proxy = create_proxy(new_cls._render)

        # Create auto state update property accessors
        for attr in list(dir(new_cls)):
            attr_value = getattr(new_cls, attr)
            if isinstance(attr_value, State):
                setattr(new_cls, attr, cls.create_state_accessor(attr, attr_value.init_value))
            elif isinstance(attr_value, Prop):
                if attr_value.is_required:
                    new_cls._props_required.add(attr)
                setattr(new_cls, attr, cls.create_prop_accessor(attr, attr_value.default_value))
                new_cls._props_defined.add(attr)
            elif isinstance(attr_value, Ref):
                setattr(new_cls, attr, cls.create_ref_accessor(attr))

        # Create css
        new_cls._selector = selector = f'cs-{token_hex(16)}'
        if env.IS_CLIENT and new_cls.style:
            css = '\n'.join(s.to_css(selector) for s in new_cls.style)

            css_node = js.document.createElement('style')
            css_node.id = new_cls._selector
            css_node.type = 'text/css'
            css_node.appendChild(js.document.createTextNode(css))

            js.document.getElementsByTagName('head')[0].appendChild(css_node)

        ReactComponentMeta._component_registry.add(new_cls)
        return new_cls


class ReactComponent(metaclass=ReactComponentMeta):
    _render_context: ClassVar[Optional[ReactComponent]] = None
    _render_proxy: ClassVar[JsProxy]
    _allow_unexpected_props: ClassVar[bool] = False
    _allow_dunder_init: ClassVar[bool] = False
    _allow_render_exceptions: ClassVar[bool] = False
    _props_defined: ClassVar[set[str]]
    _props_required: ClassVar[set[str]]
    _selector: ClassVar[str]

    _set_react_state: JsProxy = None
    _react_state = 0
    _obj_proxy: JsProxy
    _props_proxy: JsProxy
    _load_proxy: JsProxy
    _unload_proxy: JsProxy
    _parent_selector: Optional[str] = None
    _class: set[str]
    _state_values: dict[str, Any]
    _props: dict[str, Any]
    _refs: dict[str, JsProxy]

    children: tuple[TReactComponent] = ()
    style: tuple[Style] = ()

    def render(self):
        raise NotImplementedError

    def on_load(self):
        pass

    def on_unload(self):
        pass

    @classmethod
    def __class_getitem__(cls: Type[TReactComponent], _class: str) -> Type[TReactComponent]:
        return partial(cls, _class=_class)

    @classmethod
    def _remove_class(cls):
        assert env.IS_RELOAD_ENABLED

        # Remove css
        node = js.document.getElementById(cls._selector)
        if node is not None:
            node.remove()

        cls._render_proxy.destroy()

    @staticmethod
    def __new__(cls: Type[TReactComponent], *children, _class='', **props) -> TReactComponent:
        if env.IS_RELOAD_ENABLED and not issubclass(cls, (ReactReloadWrapperComponent, ReactImportComponent)):
            reloader_cls = ReactReloadWrapperComponent._get_cls(cls)
            instance = reloader_cls(*children, _class=_class, **props)
        else:
            # Check all props passed are expected
            if not cls._allow_unexpected_props:
                unknown_props = set(props.keys()) - cls._props_defined
                if unknown_props:
                    raise ValueError(f'Unexpected props {sorted(unknown_props)} passed to {cls}')

            # Check if any missing props not passed
            missing_props = cls._props_required - set(props.keys())
            if missing_props:
                raise ValueError(f'Missing props {sorted(missing_props)} for {cls}')

            if not cls._allow_dunder_init and getattr(cls, '__init__') and cls.__init__ is not object.__init__:
                print(f'Warning: {cls} has __init__ defined, this likely is incorrect', file=sys.stderr)

            instance = super().__new__(cls)
            instance._class = set(_class.split())
            instance._state_values = {}
            instance._props = props
            instance._refs = {}
            instance.children = children

            # Set selectors
            if ReactComponent._render_context is not None:
                selector = ReactComponent._render_context._selector
                if not env.IS_RELOAD_ENABLED:
                    # Assert not checked with reload, as with reload, props are reused
                    assert selector not in instance._props, selector
                instance._props[selector] = ''
                instance._parent_selector = selector

        return instance

    def __call__(self, *children):
        if self.children:
            raise RuntimeError('Children already defined')
        self.children = children
        return self

    @staticmethod
    @html.Tag._init_hook
    def _html_tag_init_hook(tag: html.Tag):
        if ReactComponent._render_context is not None:
            selector = ReactComponent._render_context._selector
            tag.attrs[selector] = ''

    @classmethod
    def _render(cls, render_props: JsProxy, children: JsProxy):
        assert ReactComponent._render_context is None
        try:
            instance, set_instance = ReactJS.useState(None)
            if instance is None:
                instance: TReactComponent = render_props._obj.unwrap()

                # Wrap instance with list to prevent react calling it, see useState docs
                instance._obj_proxy = create_proxy([instance], roundtrip=True)
                instance._load_proxy = create_proxy(instance._load, roundtrip=True)
                instance._unload_proxy = create_proxy(instance._unload, roundtrip=True)
                instance._props_proxy = render_props
                set_instance(instance._obj_proxy)
            else:
                instance: TReactComponent = instance.unwrap()[0]

            # Set render context
            # Any components and JSProxy created in this context is associated to this instance
            ReactComponent._render_context = instance

            # Setup update hook and unload hook
            _, instance._set_react_state = ReactJS.useState(0)
            ReactJS.useEffect(instance._load_proxy, to_js([]))

            # Render prop update
            if instance._props_proxy != render_props:
                # Clean up old props
                instance._props_proxy._obj.destroy()
                instance._props_proxy = render_props

                # Swap new props and children over from new obj
                new_obj = render_props._obj.unwrap()
                instance._props = new_obj._props
                instance.children = new_obj.children

            output = instance.render()
            if isinstance(output, html.Tag):
                output._class |= instance._class
                if instance._parent_selector is not None:
                    output.attrs[instance._parent_selector] = ''
            elif isinstance(output, ReactComponent):
                output._class |= instance._class
                if instance._parent_selector is not None:
                    output._props[instance._parent_selector] = ''

            return to_react_element(output)

        except Exception as exc:
            if cls._allow_render_exceptions:
                raise
            import traceback
            js.window.console.error(traceback.format_exc(limit=100))
            return f'Error: {exc}'
        finally:
            ReactComponent._render_context = None

    def _update(self):
        self._react_state = (self._react_state + 1) % 8192
        self._set_react_state(self._react_state)

    def _load(self) -> JsProxy:
        self.on_load()
        return self._unload_proxy

    def _unload(self):
        self.on_unload()
        self._obj_proxy.destroy()
        self._load_proxy.destroy()
        self._unload_proxy.destroy()
        self._props_proxy._obj.destroy()

    def _create_root(self, element_id=None) -> JsProxy:
        return create_root(self, element_id=element_id)


class ReactImportComponent(ReactComponent):
    _allow_unexpected_props = True
    _allow_dunder_init = True
    _component = None

    def render(self) -> JsProxy:
        props = to_js_obj(to_camel_case_attrs(self._props))
        children = (to_react_element(c) for c in self.children or ())
        return ReactJS.createElement(self._component, props, *children)


class ReactReloadWrapperComponent(ReactComponent):
    # Module name -> (Component name -> Reload wrapper subclass)
    _subclass_registry: ClassVar[dict[str, dict[str, Type[ReactReloadWrapperComponent]]]] = defaultdict(dict)
    _instance_registry: ClassVar[set[ReactReloadWrapperComponent]]

    _allow_unexpected_props = True
    _allow_dunder_init = True

    _component_cls: Type[TReactComponent]
    _component_instance: TReactComponent = None

    @classmethod
    def _get_cls(cls, component_cls: Type[ReactComponent]):
        # New reloader wrapper subclass created for each component class, by name
        module_name = component_cls.__module__
        component_name = component_cls.__qualname__
        if component_name not in cls._subclass_registry[module_name]:
            cls._subclass_registry[module_name][component_name] = type(
                f'ReactReloadWrapperComponent<{module_name}.{component_name}>',
                (cls, ),
                {
                    '_component_cls': component_cls,
                    '_instance_registry': WeakSet(),
                },
            )
        return cls._subclass_registry[module_name][component_name]

    @classmethod
    def _reload(cls, module):
        assert cls._component_cls
        component_cls = getattr(module, cls._component_cls.__name__, None)
        if component_cls is None:
            print(f'Unable to find `{component_cls.__name__}` in reloaded module')
            return

        # Clean up old and set new class
        cls._component_cls._remove_class()
        cls._component_cls = component_cls

        # Update instances
        for instance in cls._instance_registry:
            instance._component_instance = None
            if instance._set_react_state is not None:
                instance._update()

    def on_unload(self):
        self._instance_registry.remove(self)

    def render(self):
        assert self._component_cls
        if self._component_instance is None:
            # Manually create to avoid ReactComponent.__new__() recursion
            self._component_instance = object.__new__(self._component_cls)
            self._component_instance._class = self._class
            self._component_instance._state_values = {}
            self._component_instance._props = self._props
            self._component_instance._refs = {}
            self._component_instance.children = self.children

            # Use reload wrapper state update
            self._component_instance._update = self._update

            # Set selectors
            self._selector = self._component_instance._selector
            self._component_instance._parent_selector = self._parent_selector

            # Only add to registry after render, prevents adding transient instances
            self._instance_registry.add(self)
        else:
            # Just update props and children
            self._component_instance._props = self._props
            self._component_instance.children = self.children

        return self._component_instance


class ReactImportModule:
    def __init__(self, module_name: str, features: Optional[list[str]] = None) -> None:
        self.module_name = module_name
        self.module = import_module(module_name, features=features)
        self.components = {}

    def __getattr__(self, component_name: str) -> ReactImportComponent:
        if component_name not in self.components:
            component = getattr(self.module, component_name)
            self.components[component_name] = type(
                f'ReactImportComponent<{self.module_name}.{component_name}>',
                (ReactImportComponent, ),
                {'_component': component},
            )
        return self.components[component_name]


Component = ReactComponent
