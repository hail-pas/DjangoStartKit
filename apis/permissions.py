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


class AuthorizedServicePermission(
    BasePermission
):
    def has_permission(self, request, view):
        request.caller = None
        identifier = request.headers.get('x-identifier')
        timestamp = request.headers.get("x-timestamp")
        sign_str = request.headers.get("x-sign")
        if not all([identifier, timestamp, sign_str]):
            logger.warning("参数不全")
            return False
        # caller =
        caller = None
        if not caller:
            logger.warning("Identifier未找到")
            return False
        if request.method.upper() in ['GET', 'DELETE']:
            sign_data = request.GET.dict()
        else:
            sign_data = request.data.dict()
        logger.debug(f"sign_data: {sign_data}")
        if not timestamp:
            logger.warning("缺少时间戳")
            return False
        try:
            timestamp = int(timestamp)
        except ValueError:
            logger.warning("时间戳格式错误")
            return False
        if not sign_str:
            logger.warning("签名丢失")
            return False
        if int(time.time()) - timestamp > 120 or int(time.time()) - timestamp < -120:
            logger.warning("请求过期")
            return False
        # sign_data 生成签名
        sign_data_str = "".join(join_params(sign_data, initial=True, filter_none=True))
        sign_data_str = f"{sign_data_str}&api_key={caller.api_key}&timestamp={timestamp}"
        logger.debug(f"sign_data_str: {sign_data_str}")
        # print(sign_data)
        # print(sign_data_str)
        # print(caller.sign_key)
        # print(caller.api_key)
        if not SignAuth(caller.sign_key).verify(sign_str, sign_data_str):
            logger.warning("签名校验失败")
            return False
        request.caller = caller
        return True
