import enum


@enum.unique
class DeviceCode(str, enum.Enum):
    mobile = "mobile"
    web = "web"
