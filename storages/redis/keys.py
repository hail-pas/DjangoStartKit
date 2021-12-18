from enum import Enum, unique


@unique
class RedisSearchIndex(str, Enum):
    AnalysisIndex = "AnalysisIndex"


@unique
class RedisCacheKey(str, Enum):
    # Redis锁 Key
    redis_lock = "redis_lock_{}"
    redis_can = "redis_new_can_{}"
    AnalysisPrefix = RedisSearchIndex.AnalysisIndex.value + ":{}"
