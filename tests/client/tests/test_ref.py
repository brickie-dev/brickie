from brickie import Component
from brickie import html as H
from brickie.client import prop, ref


class Child(Component):
    ref = prop()

    def render(self):
        return H.span(ref=self.ref)('test')


class App(Component):
    el_div = ref()
    el_child = ref()

    def on_load(self):
        assert self.el_div.current
        assert self.el_child.current

    def render(self):
        return H.div(ref=self.el_div) (
            Child(ref=self.el_child)
        )
