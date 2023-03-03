import pytest

from brickie.client.router import RouteTree


def test_route_tree_insert_and_match():
    route_tree = RouteTree()
    route_tree.insert('/test/path', 'item')
    matched = route_tree.match('test/path')
    assert matched.item == 'item'
    matched = route_tree.match('test/path/other')
    assert matched is None

    with pytest.raises(ValueError):
        route_tree.insert('test/path', 'item')


def test_route_tree_with_params():
    route_tree = RouteTree()
    route_tree.insert('/test/path/:param', 'item')
    matched = route_tree.match('test/path/20')
    assert matched.item == 'item'
    assert matched.params == ('20', )

    with pytest.raises(ValueError):
        route_tree.insert('/test/path/:other', 'item')

    route_tree.insert('/test/path/:other/blah', 'item_blah')
    matched = route_tree.match('test/path/20')
    assert matched.item == 'item'
    assert matched.params == ('20', )
    matched = route_tree.match('test/path/30/blah')
    assert matched.item == 'item_blah'
    assert matched.params == ('30', )


def test_route_tree_remove():
    route_tree = RouteTree()
    route_tree.insert('/test/path', 'item')
    assert route_tree.remove('/test/path') == 'item'

    route_tree.insert('/test/path', 'item')
    with pytest.raises(ValueError):
        route_tree.remove('/test')
    assert route_tree.remove('/test/path') == 'item'
    with pytest.raises(ValueError):
        route_tree.remove('test')


def test_route_tree_remove_with_params():
    route_tree = RouteTree()
    route_tree.insert('/test/path/:param', 'item')

    with pytest.raises(ValueError):
        route_tree.remove('/test/path/test')
    with pytest.raises(ValueError):
        route_tree.remove('/test/path/:param/blah')

    assert route_tree.remove('/test/path/:param') == 'item'
    with pytest.raises(ValueError):
        route_tree.remove('/test/path/:param')
