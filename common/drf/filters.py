from django import forms
from django_filters import Filter
from django_filters.constants import EMPTY_VALUES

from common.utils import datetime_to_timestamp


class DateTimeToTimeStampFilter(Filter):
    field_class = forms.DateTimeField

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        if self.distinct:
            qs = qs.distinct()
        lookup = '%s__%s' % (self.field_name, self.lookup_expr)
        qs = self.get_method(qs)(**{lookup: datetime_to_timestamp(value)})
        return qs
