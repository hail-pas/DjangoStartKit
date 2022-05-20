from drf_yasg import openapi

from core.restful import CustomOpenAPISchemaGenerator

schema_generator = CustomOpenAPISchemaGenerator(info=openapi.Info(title="DjangoStartKit API", default_version=""),)

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
        if not path.endswith("/"):
            raise RuntimeError(f"路由{path}未使用斜杠结尾")
        API_DICT[f"{k.upper()}:{path}"] = v
