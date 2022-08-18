from enum import Enum, unique


@unique
class RedisSearchIndex(str, Enum):
    AnalysisIndex = "AnalysisIndex"


@unique
class RedisCacheKey(str, Enum):
    # Redis锁 Key
    ProfileOnline = "Profile:Online"  # bitmap
    # {"Group": {"count": int, "message_id": int}, "Dialog": {"count": int, "message_id": int}} 数量和起始信息id
    ProfileGroupUnreadInfo = "Profile:UnRead:{profile_id}:{chat_unique_id}"
    RedisLock = "redis_lock_{}"
    AnalysisPrefix = RedisSearchIndex.AnalysisIndex.value + ":{}"
