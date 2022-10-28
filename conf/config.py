import os
import multiprocessing
from typing import Any, Dict, Literal, Optional
from pathlib import Path
from functools import lru_cache

import ujson
from pydantic import BaseModel, BaseSettings, validator

from conf.enums import Environment

BASE_DIR = Path(__file__).resolve().parent.parent

ENVIRONMENT = os.environ.get("environment", Environment.development.value.lower())

CONFIG_FILE_PREFIX = str(BASE_DIR.absolute()) + f"/conf/content/{ENVIRONMENT}"

CONFIG_FILE_EXTENSION = "json"


class HostAndPort(BaseModel):
    HOST: str
    PORT: Optional[int]


class Relational(HostAndPort):
    USERNAME: str
    PASSWORD: str
    DB: str


class Redis(HostAndPort):
    USERNAME: Optional[str] = None
    PASSWORD: Optional[str] = None
    DB: int = 0


class Oss(BaseModel):
    ACCESS_KEY_ID: str
    ACCESS_KEY_SECRET: str
    ENDPOINT: str
    EXTERNAL_ENDPOINT: Optional[str]
    BUCKET_NAME: str
    CNAME: Optional[str]  # 自定义域名绑定
    BUCKET_ACL_TYPE: Optional[str] = "private"
    EXPIRE_TIME: int = 60
    MEDIA_LOCATION: Optional[str]
    STATIC_LOCATION: Optional[str]


class Server(HostAndPort):
    WORKERS_NUM: int = multiprocessing.cpu_count() * int(os.getenv("WORKERS_PER_CORE", "2")) + 1
    WHITELIST: list = []
    REQUEST_SCHEME: str = "https"


class Project(BaseModel):
    NAME: str = "DjangoStartKit"
    DEBUG: bool = False
    ENVIRONMENT: str = Environment.production.value
    DESCRIPTION: str = "Django-start-kit"
    LANGUAGE_CODE: str = "zh-hans"
    TIME_ZONE: str = "Asia/Shanghai"
    USE_TZ: str = False
    BASE_DIR = BASE_DIR

    @validator("ENVIRONMENT", allow_reuse=True)
    def check_if_environment_in(cls, v):  # noqa
        env_options = [e.value for e in Environment]
        assert v in env_options, f'Illegal environment config value, options: {",".join(env_options)}'
        return v

    @validator("DEBUG", allow_reuse=True)
    def check_debug_value(cls, v: Optional[str], values: Dict[str, Any]):  # noqa
        if "ENVIRONMENT" in values.keys():
            assert not (
                v and values["ENVIRONMENT"] == Environment.production.value
            ), "Production cannot set with debug enabled"
        return v


class Hbase(BaseModel):
    SERVERS: list = []


class Kafka(BaseModel):
    SERVERS: list = []


class Jwt(BaseModel):
    SECRET: str
    AUTH_HEADER_PREFIX: str = "JWT"
    EXPIRATION_DELTA_MINUTES: int = 432000
    REFRESH_EXPIRATION_DELTA_DELTA_MINUTES: int = 4320


class Aes(BaseModel):
    SECRET: Optional[str]


class K8s(HostAndPort):
    NAMESPACE: str
    IMAGE: str
    PVC_NAME: str
    CONFIG_FILE: Optional[str] = ""
    CONFIG_MAP_NAME: Optional[str] = ""


class ThirdApiConfig(HostAndPort):
    protocol: Literal["https", "http", "rpc"] = "https"
    timeout: int = 6
    extras: Optional[dict]


class UroraConfig(BaseModel):  # noqa
    """
    极光
    """

    app_key: str
    master_secret: str


class ThirdApiConfigs(BaseModel):
    URORA: UroraConfig  # noqa


class LocalConfig(BaseSettings):
    """
    全部的配置信息
    """

    PROJECT: Project

    SERVER: Server

    RELATIONAL: Relational

    REDIS: Optional[Redis]

    OSS: Optional[Oss]

    JWT: Jwt

    AES: Optional[Aes]

    HBASE: Optional[Hbase]

    KAFKA: Optional[Kafka]  # noqa

    K8S: Optional[K8s]

    THIRD_API_CONFIGS: Optional[ThirdApiConfigs]

    # ApiInfo

    # API_V1_ROUTE: str = "/api"
    # OPED_API_ROUTE: str = "/api/openapi.json"

    # STATIC_PATH: str = "/static"
    # STATIC_DIR: str = f"{ROOT}/static"

    @property
    def DATABASES(self) -> dict:
        return {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": self.RELATIONAL.DB,
                "USER": self.RELATIONAL.USERNAME,
                "PASSWORD": self.RELATIONAL.PASSWORD,
                "HOST": self.RELATIONAL.HOST,
                "PORT": self.RELATIONAL.PORT,
                # "OPTIONS": {"charset": "utf8mb4", "use_unicode": True},
                "TEST": {
                    "ENGINE": "sqlite3",
                    "NAME": f"test-{self.RELATIONAL.DB}",
                    "CHARSET": "utf8mb4",
                    "COLLATION": "utf8mb4_bin",
                },
            },
        }

    class Config:
        case_sensitive = True
        env_file_encoding = "utf-8"

        @classmethod
        def customise_sources(
            cls, init_settings, env_settings, file_secret_settings,  # noqa
        ):
            def json_config_settings_source(settings: BaseSettings) -> Dict[str, Any]:
                encoding = settings.__config__.env_file_encoding
                return ujson.loads(Path(".".join([CONFIG_FILE_PREFIX, CONFIG_FILE_EXTENSION])).read_text(encoding))

            return (
                init_settings,
                json_config_settings_source,
                file_secret_settings,
            )


@lru_cache()
def get_local_configs() -> LocalConfig:
    return LocalConfig()


local_configs: LocalConfig = get_local_configs()
