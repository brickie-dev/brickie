from typing import TypeVar, Union

TStyle = TypeVar('TStyle', bound='Style')


class Style:
    def __init__(self, selector: str):
        self.selector = selector
        self.properties = {}

    def __call__(self, **properties: Union[str, int, float]) -> TStyle:
        self.properties = {
            key.replace('_', '-'): value
            for key, value in properties.items()
        }
        return self

    def to_css(self, attr_selector=None) -> str:
        properties = ';'.join(
            f'{key}: {value}'
            for key, value in self.properties.items()
        )
        return f'{self.selector}[{attr_selector or ""}] {{ {properties} }}'
