from redisearch import Client

from storages.redis import get_sync_redis
from storages.redis.keys import RedisSearchIndex


class SerializableClient(Client):
    def search(self, query):
        result = super(SerializableClient, self).search(query)
        result.docs = [i.__dict__ for i in result.docs]
        return result


def get_redis_search_client(index: RedisSearchIndex) -> Client:
    if not isinstance(index, RedisSearchIndex):
        raise RuntimeError(f"index {index} is not RedisSearchIndex type")
    return SerializableClient(index.value, conn=get_sync_redis())
