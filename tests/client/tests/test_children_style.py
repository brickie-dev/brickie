import js

from brickie import Component
from brickie import html as H
from brickie.client import Style, ref


class App(Component):
    el = ref()

    def on_load(self):
        assert self.el.current
        style = js.window.getComputedStyle(self.el.current)
        assert style.color == 'red'

    def render(self):
        return H.div(
            H.span['test'](ref=self.el),
        )

    style = [
        Style('.test') (
            color='red',
        ),
    ]
