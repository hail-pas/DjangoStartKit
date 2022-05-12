from django.core import validators
from django.utils.deconstruct import deconstructible


@deconstructible
class PhoneNumberValidator(validators.RegexValidator):
    regex = r"^1[3-9]\d{9}$"
    message = "请正确填写手机号"
    flags = 0
