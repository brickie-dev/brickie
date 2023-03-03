from brickie import Component
from brickie import html as H
from brickie.client import Style, ref
from brickie.client.react import ReactImportModule

mui = ReactImportModule('@mantine/core')


class App(Component):
    el = ref()

    def on_load(self):
        assert self.el.current

    def render(self):
        return mui.Button['button'](ref=self.el)
