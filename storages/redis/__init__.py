import asyncio

import redis as s_redis
import aioredis

from conf.config import local_configs


class RedisUtil:
    """
    同步Redis操作, 使用 r 可以调用redis报api
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
        host=local_configs.REDIS.HOST,
        port=local_configs.REDIS.PORT,
        username=local_configs.REDIS.USERNAME,
        password=local_configs.REDIS.PASSWORD,
        db=local_configs.REDIS.DB,
        **kwargs,
    ):
        cls._host = host
        cls._port = port
        cls._password = password
        cls._extra_kwargs = kwargs
        cls._pool = s_redis.ConnectionPool(host=host, port=port, username=username, password=password, db=db, **kwargs)
        cls.r = s_redis.Redis(connection_pool=cls._pool)  # type:s_redis.Redis

    @classmethod
    def get_pool(cls, db: int = 0) -> s_redis.ConnectionPool:
        assert cls._pool, "must call init first"
        if db == local_configs.REDIS.DB:
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


class AsyncRedisUtil:
    """
    异步redis操作
    """

    _pool = None
    r: aioredis.Redis = None

    @classmethod
    async def init(
        cls,
        host=local_configs.REDIS.HOST,
        port=local_configs.REDIS.PORT,
        username=local_configs.REDIS.USERNAME,
        password=local_configs.REDIS.PASSWORD,
        db=local_configs.REDIS.DB,
        **kwargs,
    ):
        # redis://user:secret@localhost:6379/0?foo=bar&qux=baz
        auth_string = ""
        if username and password:
            auth_string = f"{username}:{password}@"
        cls._pool = await aioredis.create_redis_pool(
            f"redis://{auth_string}{host}:{port}", password=password, db=db, **kwargs
        )
        cls.r = cls._pool
        return cls._pool

    @classmethod
    async def get_pool(cls):
        assert cls._pool, "must call init first"
        return cls._pool

    @classmethod
    async def _exp_of_none(cls, *args, exp_of_none, callback):
        if not exp_of_none:
            return await getattr(cls._pool, callback)(*args)
        key = args[0]
        tr = cls._pool.multi_exec()
        fun = getattr(tr, callback)
        exists = await cls._pool.exists(key)
        if not exists:
            fun(*args)
            tr.expire(key, exp_of_none)
            ret, _ = await tr.execute()
        else:
            fun(*args)
            ret = (await tr.execute())[0]
        return ret

    @classmethod
    async def set(cls, key, value, exp=None):
        assert cls._pool, "must call init first"
        await cls._pool.set(key, value, expire=exp)

    @classmethod
    async def get(cls, key, default=None):
        assert cls._pool, "must call init first"
        value = await cls._pool.get(key)
        if value is None:
            return default
        return value

    @classmethod
    async def hget(cls, name, key, default=0):
        """
        缓存清除，接收list or str
        """
        assert cls._pool, "must call init first"
        v = await cls._pool.hget(name, key)
        if v is None:
            return default
        return v

    @classmethod
    async def get_or_set(cls, key, default=None, value_fun=None):
        """
        获取或者设置缓存
        """
        assert cls._pool, "must call init first"
        value = await cls._pool.get(key)
        if value is None and default:
            return default
        if value is not None:
            return value
        if value_fun:
            value, exp = await value_fun()
            await cls._pool.set(key, value, expire=exp)
        return value

    @classmethod
    async def delete(cls, key):
        """
        缓存清除，接收list or str
        """
        assert cls._pool, "must call init first"
        return await cls._pool.delete(key)

    @classmethod
    async def sadd(cls, name, values, exp_of_none=None):
        assert cls._pool, "must call init first"
        return await cls._exp_of_none(name, values, exp_of_none=exp_of_none, callback="sadd")

    @classmethod
    async def hset(cls, name, key, value, exp_of_none=None):
        assert cls._pool, "must call init first"
        return await cls._exp_of_none(name, key, value, exp_of_none=exp_of_none, callback="hset")

    @classmethod
    async def hincrby(cls, name, key, value=1, exp_of_none=None):
        assert cls._pool, "must call init first"
        return await cls._exp_of_none(name, key, value, exp_of_none=exp_of_none, callback="hincrby")

    @classmethod
    async def hincrbyfloat(cls, name, key, value, exp_of_none=None):
        assert cls._pool, "must call init first"
        return await cls._exp_of_none(name, key, value, exp_of_none=exp_of_none, callback="hincrbyfloat")

    @classmethod
    async def incrby(cls, name, value=1, exp_of_none=None):
        assert cls._pool, "must call init first"
        return await cls._exp_of_none(name, value, exp_of_none=exp_of_none, callback="incrby")

    @classmethod
    async def close(cls):
        cls._pool.close()
        await cls._pool.wait_closed()


asyncio.run(AsyncRedisUtil.init())
