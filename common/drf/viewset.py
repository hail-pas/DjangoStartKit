from functools import lru_cache

from rest_framework import serializers

from common.drf.mixins import RestModelViewSet
from common.drf.serializers import CustomModelSerializer

serializer_class_count = 1


class hashabledict(dict):
    def __hash__(self):
        return hash(tuple(sorted(self.items())))


@lru_cache(maxsize=255)
def get_dynamic_model_serializer_class(
    model_cls,
    parent_cls=(CustomModelSerializer,),
    fields: tuple = None,
    exclude: tuple = None,
    extra_fields: tuple = None,
    kwargs: hashabledict = None,
):
    """动态获取序列化model类

    Args:
        model_cls (class): Django Model
        fields (tuple, optional): 制定的字段，为空或None时则为全部字段，全部自动包括django model的property. Defaults to None.
        extra_fields (tuple, optional): 额外自定义字段. Defaults to None.
        kwargs (hashabledict, optional): 配合extra_fields定义其他字段. Defaults to None.

    Raises:
        ValidationError: _description_

    Returns:
        _type_: _description_
    """
    if not kwargs:
        kwargs = hashabledict()

    if not fields and not exclude:
        fields = [
            *[i.name for i in model_cls._meta.fields],
            *[p for p in dir(model_cls) if p != "self" and isinstance(getattr(model_cls, p), property)],
        ]
    # else:
    #     fields = list(fields)

    if extra_fields:
        fields = list(fields)
        fields.extend(list(extra_fields))

    global serializer_class_count

    serializer_class_count += 1

    class ParentRecordSerializer(*parent_cls):
        class Meta:
            model = model_cls
            ref_name = f"Dynamic{model_cls.__name__}Serializer{serializer_class_count}"

        def validate(self, attrs):
            attrs = super().validate(attrs)
            if hasattr(model_cls, "create_update_validate"):
                attrs = model_cls.create_update_validate(attrs, self.instance)
            return attrs

    if fields:
        setattr(ParentRecordSerializer.Meta, "fields", list(set(fields)))
    if exclude:
        setattr(ParentRecordSerializer.Meta, "exclude", list(set(exclude)))

    return type(f"Dynamic{model_cls.__name__}Serializer{serializer_class_count}", (ParentRecordSerializer,), kwargs)


@lru_cache(maxsize=255)
def get_dynamic_model_viewset(
    model_cls,
    parent_cls: tuple = (RestModelViewSet,),
    queryset_filters: tuple = ([], {}),
    select_related_fields: tuple = None,
    prefetch_related_fields: tuple = None,
    need_search_fields: tuple = None,
    need_filter_fields=None,  # hashabledict or tuple
    specify_filter_class=None,  # FilterClass
    specify_http_method_names: tuple = ("get", "post", "put", "patch", "delete", "head", "options", "trace"),
    list_fields: tuple = None,
    list_exclude_fields: tuple = None,
    detail_fields: tuple = None,
    editable_fields: tuple = None,
    editable_exclude_fields: tuple = None,
    create_fields: tuple = None,
    create_exclude_fields: tuple = None,
    get_other_serializer_class: callable = None,
    other_things: hashabledict = None,
):
    class ParentRecordViewset(*parent_cls):
        # f"""{model_cls.Meta.verbose_name}"""

        # ====== queryset
        _model_cls = model_cls

        queryset = model_cls.objects.filter()
        if queryset_filters:
            _args = queryset_filters[0]
            _kwargs = queryset_filters[1]
            queryset = queryset.filter(*_args, **_kwargs)
        if select_related_fields:
            queryset.select_related(*select_related_fields)
        if prefetch_related_fields:
            queryset.prefetch_related(*prefetch_related_fields)

        serializer_class = get_dynamic_model_serializer_class(model_cls=model_cls)

        # all fields
        all_fields = tuple([i.name for i in model_cls._meta.fields])
        property_fields = tuple(
            [p for p in dir(model_cls) if p != "self" and isinstance(getattr(model_cls, p), property)]
        )

        # ======search/filer
        search_fields = None
        if need_search_fields:
            search_fields = need_search_fields

        filter_fields = need_filter_fields
        filter_class = None
        if specify_filter_class:

            class _FilterClass(specify_filter_class):
                class Meta:
                    model = model_cls
                    fields = need_filter_fields

            filter_class = _FilterClass

        # specify_http_names
        http_method_names = specify_http_method_names

        def get_editable_fields(self):
            if editable_fields:
                return editable_fields
            elif editable_exclude_fields:
                return tuple(set(self.all_fields) - set(editable_exclude_fields + ("id",)))
            return tuple()

        def get_create_fields(self):
            if create_fields:
                return create_fields
            elif create_exclude_fields:
                return tuple(set(self.all_fields) - set(create_exclude_fields + ("id",)))
            return tuple()

        def get_queryset(self):
            if getattr(self, "swagger_fake_view", False):
                # queryset just for schema generation metadata
                return self.queryset.none()  # noqa
            return self.queryset.filter()

        def get_serializer_class(self):
            """动态获取序列化类"""
            if self.action in ["list"]:
                if list_fields:
                    serializer_class = get_dynamic_model_serializer_class(
                        model_cls=model_cls, fields=tuple(set(list_fields) - set(list_exclude_fields or []))
                    )
                else:
                    serializer_class = get_dynamic_model_serializer_class(
                        model_cls=model_cls,
                        fields=tuple(set(self.all_fields + self.property_fields) - set(list_exclude_fields or [])),
                    )
            elif self.action in ["retrieve"]:
                if detail_fields:
                    serializer_class = get_dynamic_model_serializer_class(model_cls=model_cls, fields=detail_fields)
                else:
                    serializer_class = get_dynamic_model_serializer_class(model_cls=model_cls, fields=self.all_fields)
            elif self.action in ["create"]:
                serializer_class = get_dynamic_model_serializer_class(
                    model_cls=model_cls, fields=self.get_create_fields()
                )
            elif self.action in ["update", "partial_update"]:
                serializer_class = get_dynamic_model_serializer_class(
                    model_cls=model_cls, fields=self.get_editable_fields()
                )
            elif get_other_serializer_class:
                # 其他方法的序列化器
                serializer_class = get_other_serializer_class(self)
            else:
                return self.serializer_class
            return serializer_class

    if not other_things:
        other_things = {}

    return type(f"{model_cls.__name__}ViewSet", (ParentRecordViewset,), other_things)
