import json

from functools import partial
from typing import Type, TypeVar

TAGS = (
    'a', 'abbr', 'address', 'area', 'article', 'aside', 'audio',
    'b', 'base', 'bdi', 'bdo', 'blockquote', 'body', 'br', 'button',
    'canvas', 'caption', 'cite', 'code', 'col', 'colgroup',
    'data', 'datalist', 'dd', 'del', 'details', 'dfn', 'dialog', 'div', 'dl', 'dt',
    'em', 'embed',
    'fieldset', 'figcaption', 'figure', 'footer', 'form',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'head', 'header', 'hgroup', 'hr', 'html',
    'i', 'iframe', 'img', 'input', 'ins',
    'kbd',
    'label', 'legend', 'li', 'link',
    'main', 'map', 'mark', 'math', 'menu', 'menuitem', 'meta', 'meter',
    'nav', 'noscript',
    'object', 'ol', 'optgroup', 'option', 'output',
    'p', 'param', 'picture', 'pre', 'progress',
    'q',
    'rb', 'rp', 'rt', 'rtc', 'ruby',
    's', 'samp', 'script', 'section', 'select', 'slot', 'small', 'source', 'span',
    'strong', 'style', 'sub', 'summary', 'sup', 'svg',
    'table', 'tbody', 'td', 'template', 'textarea', 'tfoot', 'th', 'thead',
    'time', 'title', 'tr', 'track',
    'u', 'ul',
    'var', 'video',
    'wbr',
)

SINGLETON_TAGS = (
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
    'menuitem', 'meta', 'param', 'source', 'track', 'wb',
)


TTag = TypeVar('TTag', bound='Tag')


class Tag:
    _class: set[str]
    _init_hooks = set()

    @classmethod
    def __class_getitem__(cls: Type[TTag], _class: str) -> Type[TTag]:
        return partial(cls, _class=_class)

    @classmethod
    def _init_hook(cls, f):
        cls._init_hooks.add(f)
        return f

    def __init__(self, *children, _class='', **attrs) -> None:
        self._class = set(_class.split())
        self.children = children
        self.attrs = attrs
        for hook in self._init_hooks:
            hook(self)

    def __call__(self, *children) -> TTag:
        self.children = children
        return self

    def to_html(self):
        tag = self.__class__.__name__

        attrs = [
            f'{key}={json.dumps(value)}'
            for key, value in self.attrs.items()
            if value is not None
        ]
        if self._class:
            attrs.append(f'class="{" ".join(self._class)}"')

        empty_attrs = [
            key for key, value in self.attrs.items()
            if value is None
        ]

        children = ''.join(
            c.to_html() if isinstance(c, Tag) else str(c)
            for c in self.children or ()
        )
        return f'<{" ".join([tag, *empty_attrs, *attrs])}>{children}</{tag}>'


class SingletonTag(Tag):
    def __init__(self, *children, _class='', **attrs) -> None:
        if children:
            tag = self.__class__.__name__
            raise TypeError(f'Singleton tag <{tag}> cannot have children')

        self._class = set(_class.split())
        self.children = None
        self.attrs = attrs
        for hook in self._init_hooks:
            hook(self)

    def __call__(self, children):
        tag = self.__class__.__name__
        raise TypeError(f'Singleton tag <{tag}> cannot have children')

    def to_html(self):
        tag = self.__class__.__name__

        attrs = [
            f'{key}={json.dumps(value)}'
            for key, value in self.attrs.items()
            if value is not None
        ]
        if self._class:
            attrs.append(f'class="{" ".join(self._class)}"')

        empty_attrs = [
            key for key, value in self.attrs.items()
            if value is None
        ]
        return f'<{" ".join([tag, *empty_attrs, *attrs])}>'


for t in TAGS:
    if t in SINGLETON_TAGS:
        continue
    locals()[t] = type(t, (Tag, ), {})

    for t in SINGLETON_TAGS:
        locals()[t] = type(t, (SingletonTag, ), {})
