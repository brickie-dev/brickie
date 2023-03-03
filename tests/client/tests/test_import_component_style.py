import js

from brickie import Component
from brickie import html as H
from brickie.client import Style, ref
from brickie.client.react import ReactImportModule

mui = ReactImportModule('@mantine/core')


class ChildComponent(Component):
    el = ref()

    def on_load(self):
        assert self.el.current
        style = js.window.getComputedStyle(self.el.current)
        assert style.color == 'blue'
        assert getattr(style, 'background-color') == 'black'

    def render(self):
        return H.div['root'](ref=self.el)

    style = [
        Style('.root') (
            color='blue',
        ),
    ]


class ChildComponentImport(Component):
    el = ref()

    def on_load(self):
        assert self.el.current
        style = js.window.getComputedStyle(self.el.current)
        assert style.color == 'blue'
        assert getattr(style, 'background-color') == 'yellow'

    def render(self):
        return mui.Group['root'](ref=self.el)

    style = [
        Style('.root') (
            color='blue',
        ),
    ]


class App(Component):
    el_group = ref()
    el_span = ref()
    el_child = ref()

    def on_load(self):
        assert self.el_group.current
        assert self.el_span.current
        style = js.window.getComputedStyle(self.el_group.current)
        assert style.color == 'green'
        style = js.window.getComputedStyle(self.el_span.current)
        assert style.color == 'red'

    def render(self):
        return mui.Group['group'](ref=self.el_group) (
            H.span['span'](ref=self.el_span),
            ChildComponent['child'](),
            ChildComponentImport['child-import'](),
        )

    style = [
        Style('.group') (
            color='green',
        ),
        Style('.span') (
            color='red',
        ),
        Style('.child') (
            background_color='black',
        ),
        Style('.child-import') (
            background_color='yellow',
        ),
    ]
