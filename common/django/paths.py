from drf_yasg import openapi
from drf_yasg.inspectors import SwaggerAutoSchema

from core.restful import CustomAutoSchema, CustomOpenAPISchemaGenerator
from apps.permissions import URIBasedPermission


class ViewPathAutoSchema(CustomAutoSchema):
    def get_description(self, path, method):  # noqa
        """
        Determine a path description.

        This will be based on the method docstring if one exists,
        or else the class docstring.
        """
        view = self.view

        permission_classes = view.permission_classes
        if URIBasedPermission not in permission_classes:
            return "%"

        method_name = getattr(view, "action", method.lower())
        _view_path = f"{self.view.__module__}.{self.view.__class__.__name__}.{method_name}"
        _description = super().get_description(path, method)
        if not _description:
            _description = f"{method}:{path}"
        return f"{_view_path}%{_description}"


class ViewPathCustomSwaggerAutoSchema(SwaggerAutoSchema):
    def __init__(self, view, path, method, components, request, overrides, operation_keys=None):  # noqa
        super(SwaggerAutoSchema, self).__init__(view, path, method, components, request, overrides)
        self._sch = ViewPathAutoSchema()
        self._sch.view = view
        self.operation_keys = operation_keys


class ViewPathCustomOpenAPISchemaGenerator(CustomOpenAPISchemaGenerator):
    def get_operation(self, view, path, prefix, method, components, request):  # noqa
        operation_keys = self.get_operation_keys(path[len(prefix) :], method, view)
        overrides = self.get_overrides(view, method)

        view_inspector_cls = ViewPathCustomSwaggerAutoSchema

        if view_inspector_cls is None:
            return None

        view_inspector = view_inspector_cls(view, path, method, components, request, overrides, operation_keys)
        operation = view_inspector.get_operation(operation_keys)
        if operation is None:
            return None

        if "consumes" in operation and set(operation.consumes) == set(self.consumes):
            del operation.consumes
        if "produces" in operation and set(operation.produces) == set(self.produces):
            del operation.produces
        return operation


schema_generator = ViewPathCustomOpenAPISchemaGenerator(
    info=openapi.Info(title="DjangoStartKit API", default_version=""),
)

API_DICT = {}

paths, prefix = schema_generator.get_paths(
    endpoints=schema_generator.get_endpoints(None),
    components=schema_generator.reference_resolver_class("definitions", force_init=True),
    request=None,
    public=True,
)

for path, path_item in paths.items():
    operations = {i[0]: i[1].description for i in path_item.operations}  # method: description
    for k, v in operations.items():
        view_path, description = v.split("%", 1)
        if view_path:
            API_DICT[view_path] = description
