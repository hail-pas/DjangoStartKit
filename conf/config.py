import multiprocessing
import os
from functools import lru_cache
from typing import Optional, List, Dict, Any

from pydantic import BaseSettings, validator

from conf.enums import Environment

BASE_DIR = Path(__file__).resolve().parent.parent


class LocalConfig(BaseSettings):
    """
    全部的配置信息
    """
    # ProjectInfo
    PROJECT_NAME: str = "core"
    DESCRIPTION: str = "Django-start-kit"
    ENVIRONMENT: str = Environment.development.value
    DEBUG: bool = False

    SERVER_HOST: str = "localhost"
    SERVER_PORT: int = 8000

    @validator("ENVIRONMENT", allow_reuse=True)
    def check_if_environment_in(cls, v):
        env_options = [e.value for e in Environment]
        assert v in env_options, f'Illegal environment config value, options: {",".join(env_options)}'
        return v

    @validator("DEBUG", allow_reuse=True)
    def check_debug_value(cls, v: Optional[str], values: Dict[str, Any]):
        assert not (v and values[
            "ENVIRONMENT"] == Environment.production.value), f'Production cannot set with debug enabled'
        return v

    # ApiInfo

    # API_V1_ROUTE: str = "/api"
    # OPED_API_ROUTE: str = "/api/openapi.json"

    # gunicorn
    WORKERS_NUM: int = multiprocessing.cpu_count() * int(os.getenv("WORKERS_PER_CORE", "2")) + 1

    # DataBase
    # ========MySQL
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = ""
    DB_NAME: str = ""
    DB_PASSWORD: str = ""

    LANGUAGE_CODE: str = "zh-hans"
    TIME_ZONE: str = "Asia/Shanghai"
    USE_TZ: bool = False

    # =========Redis
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = None
    REDIS_DB: int = 0
    REDIS_SEARCH_DB: int = 1


    # =========HBase
    THRIFT_SERVERS: Optional[List[str]] = ["192.168.3.75:9090"]

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: Optional[List[str]] = ["localhost:9091"]

    # Template
    # TEMPLATE_PATH: str = f"{ROOT}/templates"

    # Static
    # STATIC_PATH: str = "/static"
    # STATIC_DIR: str = f"{ROOT}/static"

    # JWT
    JWT_AUTH_HEADER_PREFIX: str = "JWT"
    JWT_SECRET: str
    JWT_EXPIRATION_DELTA_MINUTES: int = 60 * 24 * 3  # token 过期时间
    JWT_REFRESH_EXPIRATION_DELTA_DELTA_MINUTES: int = 60 * 24 * 5  # 刷新token过期时间
    AES_SECRET: Optional[str]
    # SIGN_SECRET: Optional[str]

    # IP WhiteList
    HOST_WHITELIST: Optional[List[str]] = []

    @property
    def DATABASES(self) -> dict:
        return {
            'default': {
                'ENGINE': 'django.db.backends.mysql',
                'NAME': self.DB_NAME,
                'USER': self.DB_USER,
                'PASSWORD': self.DB_PASSWORD,
                'HOST': self.DB_HOST,
                'PORT': self.DB_PORT,
                'OPTIONS': {
                    'charset': 'utf8mb4',
                    'use_unicode': True,
                },
                'TEST': {
                    'CHARSET': 'utf8mb4',
                    'COLLATION': 'utf8mb4_bin',
                },
            },
        }

    class Config:
        case_sensitive = True
        env_file = str(
            BASE_DIR.absolute()) + f'/conf/envs/{os.environ.get("environment", Environment.development.value.lower())}.env'
        env_file_encoding = "utf-8"


@lru_cache()
def get_local_configs() -> LocalConfig:
    return LocalConfig()


local_configs: LocalConfig = get_local_configs()
