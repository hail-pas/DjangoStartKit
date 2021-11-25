from enum import Enum, unique


@unique
class RedisCacheKey(str, Enum):
    # Redis锁 Key
    redis_lock = "redis_lock_{}"
