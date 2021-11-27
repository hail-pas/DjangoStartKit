from rest_framework.viewsets import GenericViewSet

from common.drf import mixins


class RestModelViewSet(mixins.RestCreateModelMixin,
                       mixins.RestRetrieveModelMixin,
                       mixins.RestUpdateModelMixin,
                       mixins.RestDestroyModelMixin,
                       mixins.RestListModelMixin,
                       GenericViewSet):
    """
    返回 RestResponse
    """
    pass
