from asyncio import Future

from starlette.responses import FileResponse, JSONResponse


def create_endpoint(_f):
    async def _e(request):
        params = await request.json()
        result = await _f(*params['a'], **params['k'])
        if isinstance(result, Future):
            result = await result
        return JSONResponse({'r': result})
    return _e


def index(request):
    return FileResponse('.brickie/build/index.html')
