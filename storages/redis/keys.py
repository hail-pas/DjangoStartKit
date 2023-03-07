from enum import Enum, unique

ProjectCode = ""

RedisKeyPrefix = ProjectCode + ":"


@unique
class RedisSearchIndexPrefix(str, Enum):
    AnalysisIndex = RedisKeyPrefix + "AnalysisIndex"


@unique
class RedisCacheKey(str, Enum):
    # Redis锁 Key
    ProfileOnlineKey = RedisKeyPrefix + "Profile:Online:{profile_id}"  # 在线信息
    # 用户连接信息
    ProfileConnectionKey = RedisKeyPrefix + "Profile:Connection:{profile_id}-{device_code}"  # 一个用户最多只有两个设备的连接
    # 用户群组
    ProfileGroupSet = RedisKeyPrefix + "Profile:Group:{profile_id}"  # 用户加入的所有群组id
    # {"Group": {"count": int, "message_id": int}, "Dialog": {"count": int, "message_id": int}} 数量和起始信息id
    ProfileGroupUnreadInfo = RedisKeyPrefix + "Profile:UnRead:{profile_id}:{chat_unique_id}"
    RedisLockKey = RedisKeyPrefix + "redis_lock_{}"
    AnalysisPrefix = RedisKeyPrefix + RedisSearchIndexPrefix.AnalysisIndex.value + ":{}"
    VerifyCodeKey = RedisKeyPrefix + "Verify:{phone}:{scene}"  # 验证码 key
