import copy
import datetime
from typing import Callable
from collections import OrderedDict

from rest_framework import ISO_8601, serializers
from django.contrib.auth import authenticate
from rest_framework.utils import humanize_datetime
from rest_framework.fields import SkipField, ChoiceField, DateTimeField, empty
from django.utils.dateparse import parse_datetime
from django.utils.translation import ugettext as _
from rest_framework.relations import PKOnlyObject
from rest_framework.serializers import ALL_FIELDS, ModelSerializer
from rest_framework_jwt.serializers import JSONWebTokenSerializer, jwt_encode_handler, jwt_payload_handler

from common import messages
from storages import enums
from conf.config import local_configs
from common.utils import COMMON_TIME_STRING, format_str_to_millseconds


class CustomModelSerializer(ModelSerializer):
    # 示例前置序列化钩子, 一条数据只会执行一次
    _pre_serialize: Callable = None

    def __init__(self, instance=None, data=empty, **kwargs):
        self.simple_list = kwargs.pop("simple_list", None)
        self._pre_serialize = getattr(self.Meta, "pre_serialize", None)  # noqa
        super().__init__(instance, data, **kwargs)

    def get_field_names(self, declared_fields, info):
        """
        Returns the list of all field names that should be created when
        instantiating this serializer class. This is based on the default
        set of fields, but also takes into account the `Meta.fields` or
        `Meta.exclude` options if they have been specified.
        """
        fields = getattr(self.Meta, "fields", None)
        exclude = getattr(self.Meta, "exclude", None)

        if isinstance(fields, (set,)):
            fields = list(fields)

        if fields and fields != ALL_FIELDS and not isinstance(fields, (list, tuple)):
            raise TypeError(
                'The `fields` option must be a list or tuple or "__all__". ' "Got %s." % type(fields).__name__
            )

        if exclude and not isinstance(exclude, (list, tuple)):
            raise TypeError("The `exclude` option must be a list or tuple. Got %s." % type(exclude).__name__)

        assert not (fields and exclude), (
            "Cannot set both 'fields' and 'exclude' options on "
            "serializer {serializer_class}.".format(serializer_class=self.__class__.__name__)
        )

        assert not (fields is None and exclude is None), (
            "Creating a ModelSerializer without either the 'fields' attribute "
            "or the 'exclude' attribute has been deprecated since 3.3.0, "
            "and is now disallowed. Add an explicit fields = '__all__' to the "
            "{serializer_class} serializer.".format(serializer_class=self.__class__.__name__),
        )

        if fields == ALL_FIELDS:
            fields = None

        if fields is not None:
            # Ensure that all declared fields have also been included in the
            # `Meta.fields` option.

            # Do not require any fields that are declared in a parent class,
            # in order to allow serializer subclasses to only include
            # a subset of fields.
            required_field_names = set(declared_fields)
            for cls in self.__class__.__bases__:
                required_field_names -= set(getattr(cls, "_declared_fields", []))

            for field_name in required_field_names:
                assert field_name in fields, (
                    "The field '{field_name}' was declared on serializer "
                    "{serializer_class}, but has not been included in the "
                    "'fields' option.".format(field_name=field_name, serializer_class=self.__class__.__name__)
                )
            return fields

        # Use the default set of field names if `Meta.fields` is not specified.
        fields = self.get_default_field_names(declared_fields, info)

        property_names = [
            name for name in dir(self.Meta.model) if isinstance(getattr(self.Meta.model, name), property)  # noqa
        ]  # noqa
        if "pk" in property_names:
            property_names.remove("pk")
        fields += tuple(property_names)

        if exclude is not None:
            # If `Meta.exclude` is included, then remove those fields.
            for field_name in exclude:
                assert field_name not in self._declared_fields, (  # noqa
                    "Cannot both declare the field '{field_name}' and include "
                    "it in the {serializer_class} 'exclude' option. Remove the "
                    "field or, if inherited from a parent serializer, disable "
                    "with `{field_name} = None`.".format(  # noqa
                        field_name=field_name, serializer_class=self.__class__.__name__  # noqa  # noqa
                    )  # noqa
                )

                assert field_name in fields, (
                    "The field '{field_name}' was included on serializer "
                    "{serializer_class} in the 'exclude' option, but does "
                    "not match any model field.".format(field_name=field_name, serializer_class=self.__class__.__name__)
                )
                fields.remove(field_name)

        return fields

    def get_extra_kwargs(self):
        """
        Return a dictionary mapping field names to a dictionary of
        additional keyword arguments.
        """
        extra_kwargs = copy.deepcopy(getattr(self.Meta, "extra_kwargs", {}))

        read_only_fields = getattr(self.Meta, "read_only_fields", None)
        if isinstance(read_only_fields, (set,)):
            read_only_fields = list(read_only_fields)
        if read_only_fields is not None:
            property_names = [
                name for name in dir(self.Meta.model) if isinstance(getattr(self.Meta.model, name), property)
            ]
            if "pk" in property_names:
                property_names.remove("pk")
            read_only_fields += tuple(property_names + ["id", "delete_time", "create_time", "update_time"])
            if not isinstance(read_only_fields, (list, tuple)):
                raise TypeError(
                    "The `read_only_fields` option must be a list or tuple. "
                    "Got %s." % type(read_only_fields).__name__
                )
            for field_name in read_only_fields:
                kwargs = extra_kwargs.get(field_name, {})
                kwargs["read_only"] = True
                extra_kwargs[field_name] = kwargs

        else:
            # Guard against the possible misspelling `readonly_fields` (used
            # by the Django admin and others).
            assert not hasattr(self.Meta, "readonly_fields"), (
                "Serializer `%s.%s` has field `readonly_fields`; "  # noqa
                "the correct spelling for the option is `read_only_fields`."
                % (self.__class__.__module__, self.__class__.__name__)
            )

        return extra_kwargs

    def to_representation(self, instance):
        """
        Object instance -> Dict of primitive datatypes.
        """
        ret = OrderedDict()
        fields = self._readable_fields

        if self._pre_serialize:
            self._pre_serialize(self, instance)

        for field in fields:
            try:
                attribute = field.get_attribute(instance)
            except SkipField:
                continue
            # simple_list enum 处理
            except KeyError as e:
                if self.simple_list and field.field_name not in self.simple_list:
                    continue
                raise e

            # We skip `to_representation` for `None` values so that fields do
            # not have to explicitly deal with that case.
            #
            # For related fields with `use_pk_only_optimization` we need to
            # resolve the pk value.
            check_for_none = attribute.pk if isinstance(attribute, PKOnlyObject) else attribute
            if check_for_none is None:
                # simple_list enum 处理
                if self.simple_list:
                    if field.field_name in self.simple_list:
                        ret[field.field_name] = None
                else:
                    ret[field.field_name] = None
            else:
                # simple_list enum 处理
                if self.simple_list and isinstance(field, ChoiceField):
                    ret[field.field_name] = field.choices.get(field.to_representation(attribute))
                else:
                    if isinstance(field, ChoiceField):
                        ret[f"enum_{field.field_name}_display"] = field.choices.get(field.to_representation(attribute))
                    elif isinstance(field, DateTimeField):
                        field.format = COMMON_TIME_STRING
                    ret[field.field_name] = field.to_representation(attribute)

        return ret


class CustomJSONWebTokenSerializer(JSONWebTokenSerializer):
    def validate(self, attrs):
        credentials = {self.username_field: attrs.get(self.username_field), "password": attrs.get("password")}

        if all(credentials.values()):
            user = authenticate(**credentials)

            if user:
                if not user.is_active:
                    msg = messages.AccountDisabled
                    raise serializers.ValidationError(msg)

                payload = jwt_payload_handler(user)
                scene = attrs.get("scene")
                if scene not in enums.SceneRole.values() + user.role_names:
                    raise serializers.ValidationError(messages.UserSceneCheckFailed)
                system = attrs.get("system")
                # TODO: 校验用户登录系统合法性
                if not system:
                    system = local_configs.PROJECT.NAME
                payload["system"] = system
                payload["scene"] = scene

                return {"token": jwt_encode_handler(payload), "user": user}
            else:
                msg = messages.UserOrPasswordError
                raise serializers.ValidationError(msg)
        else:
            msg = _('Must include "{username_field}" and "password".')
            msg = msg.format(username_field=self.username_field)
            raise serializers.ValidationError(msg)


class DateTimeToTimeStampField(DateTimeField):
    def to_internal_value(self, value):
        input_formats = COMMON_TIME_STRING

        if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
            self.fail("date")

        if isinstance(value, datetime.datetime):
            return self.enforce_timezone(value)

        for input_format in input_formats:
            if input_format.lower() == ISO_8601:
                try:
                    parsed = parse_datetime(value)
                    if parsed is not None:
                        return self.enforce_timezone(parsed)
                except (ValueError, TypeError):
                    pass
            else:
                try:
                    parsed = self.datetime_parser(value, input_formats)
                    datetime_str = self.enforce_timezone(parsed)
                    return format_str_to_millseconds(datetime_str)
                except (ValueError, TypeError):
                    pass

        humanized_format = humanize_datetime.datetime_formats(input_formats)
        self.fail("invalid", format=humanized_format)
