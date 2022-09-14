import os
import multiprocessing
from typing import Any, Dict, Literal, Optional
from pathlib import Path
from functools import lru_cache

import yaml
from pydantic import BaseModel, BaseSettings, validator

from conf.enums import Environment

BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG_FILE_PREFIX = (
    str(BASE_DIR.absolute()) + f'/conf/content/{os.environ.get("environment", Environment.development.value.lower())}'
)


class HostAndPort(BaseModel):
    HOST: str
    PORT: Optional[int]


class RelationalDb(HostAndPort):
    USER: str
    PASSWORD: str
    DB: str


class Redis(HostAndPort):
    USERNAME: Optional[str] = None
    PASSWORD: Optional[str] = None
    DB: int = 0


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

    RELATIONAL_DB: RelationalDb

    REDIS: Optional[Redis]

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
                "ENGINE": "django.db.backends.mysql",
                "NAME": self.RELATIONAL_DB.DB,
                "USER": self.RELATIONAL_DB.USER,
                "PASSWORD": self.RELATIONAL_DB.PASSWORD,
                "HOST": self.RELATIONAL_DB.HOST,
                "PORT": self.RELATIONAL_DB.PORT,
                "OPTIONS": {"charset": "utf8mb4", "use_unicode": True},
                "TEST": {
                    "ENGINE": "sqlite3",
                    "NAME": f"test-{self.RELATIONAL_DB.DB}",
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
            return (
                init_settings,
                yaml_config_settings_source,
                # json_config_settings_source,
                # env_settings,
                file_secret_settings,
            )


def yaml_config_settings_source(settings: BaseSettings) -> Dict[str, Any]:
    encoding = settings.__config__.env_file_encoding
    return yaml.load(Path(CONFIG_FILE_PREFIX + ".yaml").read_text(encoding), yaml.FullLoader)


@lru_cache()
def get_local_configs() -> LocalConfig:
    return LocalConfig()


local_configs: LocalConfig = get_local_configs()
