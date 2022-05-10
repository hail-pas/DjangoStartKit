from django.forms.utils import pretty_name
from rest_framework.decorators import MethodMapper

from common.utils import underscore_to_camelcase


def camelCaseAction(methods=None, detail=None, url_path=None, url_name=None, **kwargs):
    methods = ['get'] if (methods is None) else methods
    methods = [method.lower() for method in methods]

    assert detail is not None, (
        "@action() missing required argument: 'detail'"
    )

    # name and suffix are mutually exclusive
    if 'name' in kwargs and 'suffix' in kwargs:
        raise TypeError("`name` and `suffix` are mutually exclusive arguments.")

    def decorator(func):
        func.mapping = MethodMapper(func, methods)

        func.detail = detail
        func.url_path = url_path if url_path else underscore_to_camelcase(func.__name__)
        func.url_name = url_name if url_name else func.__name__.replace('_', '-')

        # These kwargs will end up being passed to `ViewSet.as_view()` within
        # the router, which eventually delegates to Django's CBV `View`,
        # which assigns them as instance attributes for each request.
        func.kwargs = kwargs

        if 'name' not in kwargs and 'suffix' not in kwargs:
            func.kwargs['name'] = pretty_name(func.__name__)
        func.kwargs['description'] = func.__doc__ or None

        return func

    return decorator
