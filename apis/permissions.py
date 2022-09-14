import time
import logging

from rest_framework.permissions import BasePermission

from common.utils import join_params
from common.encrypt import SignAuth

logger = logging.getLogger(__name__)

_PERMISSION_APP_LABEL = "account"


class URIBasedPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated) and request.user.has_api_perm(request, view)


class AuthorizedServicePermission(BasePermission):
    def has_permission(self, request, view):
        identifier = request.headers.get("x-identifier")
        timestamp = request.headers.get("x-timestamp")
        sign_str = request.headers.get("x-sign")
        if not all([identifier, timestamp, sign_str]):
            return False
        # caller = ThirdService.objects.filter(identifier=identifier).first()
        # 替换成对应的授权调用方实例
        caller = None
        if not caller:
            return False
        if request.method in ["GET", "DELETE"]:
            sign_data = request.GET
        else:
            sign_data = request.data
        logger.debug(f"sign_data: {sign_data}")
        if not timestamp:
            return False
        if not isinstance(timestamp, int):
            return False
        if not sign_str:
            return False
        if int(time.time()) - timestamp > 120 or int(time.time()) - timestamp < -120:
            return False
        # sign_data 生成签名
        sign_data_str = join_params(sign_data)
        sign_data_str = f"{sign_data_str}&api_ky={caller.api_key}&timestamp={timestamp}"
        logger.debug(f"sign_data_str: {sign_data_str}")
        if not SignAuth(caller.sign_key).verify(sign_str, sign_data_str):
            return False
        return True
