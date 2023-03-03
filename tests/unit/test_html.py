import pytest

from brickie import html as H


@pytest.fixture(autouse=True)
def setup():
    H.Tag._init_hooks.clear()


def test_html_tag_class():
    div = H.div(_class='test')
    assert div._class == {'test'}
    assert div.to_html() == '<div class="test"></div>'

    div = H.div()
    assert div.to_html() == '<div></div>'


def test_html_singleton_tag_class():
    inp = H.input(_class='test')
    assert inp._class == {'test'}
    assert inp.to_html() == '<input class="test">'

    inp = H.input()
    assert inp.to_html() == '<input>'


def test_html_tag_init_hook():
    @H.Tag._init_hook
    def hook(tag):
        tag.done = True

    div = H.div()
    assert div.done


def test_html_singleton_tag_init_hook():
    @H.Tag._init_hook
    def hook(tag):
        tag.done = True

    div = H.input()
    assert div.done
