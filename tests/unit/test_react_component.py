import pytest

from brickie.client.react import Component, prop


def test_prop_required():
    class A(Component):
        b = prop()

    assert A._props_defined == {'b'}
    assert A._props_required == {'b'}

    A(b=2)
    with pytest.raises(ValueError, match='Unexpected props'):
        A(c=2)
    with pytest.raises(ValueError, match='Missing props'):
        A()


def test_prop_default_value():
    class A(Component):
        b = prop('test')

    assert A._props_defined == {'b'}
    assert not A._props_required

    A(b=2)
    with pytest.raises(ValueError, match='Unexpected props'):
        A(c=2)
    A()


def test_prop_unexpected():
    class A(Component):
        c = prop()

    assert A._props_defined == {'c'}

    A(c=3)
    with pytest.raises(ValueError, match='Unexpected props'):
        A(d=3)
    with pytest.raises(ValueError, match='Unexpected props'):
        A(d=3, g='test')
