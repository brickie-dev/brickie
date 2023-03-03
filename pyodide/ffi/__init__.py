class JsProxy:
    pass


def to_js(*args, **kwargs) -> JsProxy:
    raise NotImplementedError


def create_proxy(*args, **kwargs) -> JsProxy:
    raise NotImplementedError


def create_once_callable(*args, **kwargs) -> JsProxy:
    raise NotImplementedError
