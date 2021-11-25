import logging

from storages.redis import RedisUtil

logger = logging.getLogger(__name__)


def ready():
    """
    启动时触发
    :return:
    """
    RedisUtil.init()
    logger.info("Initialize Redis Successful...")

