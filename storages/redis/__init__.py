import redis as s_redis

from conf.config import local_configs


class RedisUtil:
    """
    同步Redis操作
    """

    _host = None
    _port = None
    _password = None
    _extra_kwargs = None
    _pool: s_redis.ConnectionPool = None
    r: s_redis.Redis = None

    @classmethod
    def init(
        cls,
        host=local_configs.REDIS_HOST,
        port=local_configs.REDIS_PORT,
        password=local_configs.REDIS_PASSWORD,
        db=local_configs.REDIS_DB,
        **kwargs,
    ):
        cls._host = host
        cls._port = port
        cls._password = password
        cls._extra_kwargs = kwargs
        cls._pool = s_redis.ConnectionPool(host=host, port=port, password=password, db=db, **kwargs)
        cls.r = s_redis.Redis(connection_pool=cls._pool)  # type:s_redis.Redis

    @classmethod
    def get_pool(cls, db: int = 0) -> s_redis.ConnectionPool:
        assert cls._pool, "must call init first"
        if db == local_configs.REDIS_DB:
            return cls._pool
        else:
            return s_redis.ConnectionPool(
                host=cls._host, port=cls._port, password=cls._password, db=db, **cls._extra_kwargs
            )

    @classmethod
    def _exp_of_none(cls, *args, exp_of_none, callback):
        if not exp_of_none:
            return getattr(cls.r, callback)(*args)
        with cls.r.pipeline() as pipe:
            count = 0
            while True:
                try:
                    fun = getattr(pipe, callback)
                    key = args[0]
                    pipe.watch(key)
                    exp = pipe.ttl(key)
                    pipe.multi()
                    if exp == -2:
                        fun(*args)
                        pipe.expire(key, exp_of_none)
                        ret, _ = pipe.execute()
                    else:
                        fun(*args)
                        ret = pipe.execute()[0]
                    return ret
                except s_redis.WatchError:
                    if count > 3:
                        raise s_redis.WatchError
                    count += 1
                    continue

    @classmethod
    def get_or_set(cls, key, default=None, value_fun=None):
        """
        获取或者设置缓存
        """
        value = cls.r.get(key)
        if value is None and default:
            return default
        if value is not None:
            return value
        if value_fun:
            value, exp = value_fun()
            cls.r.set(key, value, exp)
        return value

    @classmethod
    def get(cls, key, default=None):
        value = cls.r.get(key)
        if value is None:
            return default
        return value

    @classmethod
    def set(cls, key, value, exp=None):
        """
        设置缓存
        """
        return cls.r.set(key, value, exp)

    @classmethod
    def delete(cls, key):
        """
        缓存清除，接收list or str
        """
        return cls.r.delete(key)

    @classmethod
    def sadd(cls, name, values, exp_of_none=None):
        return cls._exp_of_none(name, values, exp_of_none=exp_of_none, callback="sadd")

    @classmethod
    def hset(cls, name, key, value, exp_of_none=None):
        return cls._exp_of_none(name, key, value, exp_of_none=exp_of_none, callback="hset")

    @classmethod
    def hincrby(cls, name, key, value=1, exp_of_none=None):
        return cls._exp_of_none(name, key, value, exp_of_none=exp_of_none, callback="hincrby")

    @classmethod
    def hincrbyfloat(cls, name, key, value, exp_of_none=None):
        return cls._exp_of_none(name, key, value, exp_of_none=exp_of_none, callback="hincrbyfloat")

    @classmethod
    def incrby(cls, name, value=1, exp_of_none=None):
        return cls._exp_of_none(name, value, exp_of_none=exp_of_none, callback="incrby")

    @classmethod
    def hget(cls, name, key, default=None):
        """
        缓存清除，接收list or str
        """
        v = cls.r.hget(name, key)
        if v is None:
            return default
        return v

    @classmethod
    def hgetall(cls, name, default=None):
        v = cls.r.hgetall(name)
        if v is None:
            return default
        return {k.decode("utf-8"): v.decode("utf-8") for k, v in v.items()}


RedisUtil.init()


def get_sync_redis():
    return RedisUtil.r
