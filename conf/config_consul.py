import os
from typing import Any, Dict, Optional
from pathlib import Path
from functools import lru_cache

import ujson
import consulate
from pydantic import BaseModel, BaseSettings, validator

from conf.enums import Environment

BASE_DIR = Path(__file__).resolve().parent.parent

ENVIRONMENT = os.environ.get("environment", Environment.development.value.lower())

CONFIG_FILE_PREFIX = str(BASE_DIR.absolute()) + f'/conf/content/{ENVIRONMENT + "_consul"}'

CONFIG_FILE_EXTENSION = "json"


class HostAndPort(BaseModel):
    HOST: str
    PORT: Optional[int]


class Consul(HostAndPort):
    TOKEN: Optional[str]
    TIMEOUT: int = 60
    DATACENTER: Optional[str]
    SCHEME: Optional[str]
    ADAPTER: Optional[str]


class YamlConfig(BaseSettings):
    CONSUL: Consul
    CONFIG_KEY_PREFIX: str

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


json_config = YamlConfig()

consul = consulate.Consul(
    addr=None,
    host=json_config.CONSUL.HOST,
    port=json_config.CONSUL.PORT,
    datacenter=json_config.CONSUL.DATACENTER,
    token=json_config.CONSUL.TOKEN,
    scheme=json_config.CONSUL.SCHEME,
    adapter=json_config.CONSUL.ADAPTER,
)


def get_consul_value(path, key):
    return ujson.loads(consul.kv[f"{json_config.CONFIG_KEY_PREFIX}/{ENVIRONMENT}/{path}"]).get(key)


class RelationalDb:
    HOST = get_consul_value("Relational", "HOST")
    PORT = get_consul_value("Relational", "PORT")
    USERNAME = get_consul_value("Relational", "USERNAME")
    PASSWORD = get_consul_value("Relational", "PASSWORD")
    DB = get_consul_value("Relational", "DB")


class Redis:
    HOST = get_consul_value("Redis", "HOST")
    PORT = get_consul_value("Redis", "PORT")
    USERNAME = get_consul_value("Redis", "USERNAME")
    PASSWORD = get_consul_value("Redis", "PASSWORD")
    DB = get_consul_value("Redis", "DB")


class Oss:
    ACCESS_KEY_ID = get_consul_value("Oss", "ACCESS_KEY_ID")
    ACCESS_KEY_SECRET = get_consul_value("Oss", "ACCESS_KEY_SECRET")
    ENDPOINT = get_consul_value("Oss", "ENDPOINT")
    EXTERNAL_ENDPOINT = get_consul_value("Oss", "EXTERNAL_ENDPOINT")
    BUCKET_NAME = get_consul_value("Oss", "BUCKET_NAME")
    CNAME = get_consul_value("Oss", "CNAME")
    BUCKET_ACL_TYPE = get_consul_value("Oss", "BUCKET_ACL_TYPE") or "private"
    EXPIRE_TIME = get_consul_value("Oss", "EXPIRE_TIME") or 60
    MEDIA_LOCATION = get_consul_value("Oss", "MEDIA_LOCATION")
    STATIC_LOCATION = get_consul_value("Oss", "STATIC_LOCATION")


class Server:
    HOST = get_consul_value("Server", "HOST")
    PORT = get_consul_value("Server", "PORT")
    WHITELIST = get_consul_value("Server", "WHITELIST")
    REQUEST_SCHEME = get_consul_value("Server", "REQUEST_SCHEME") or "https"


class Project:
    NAME = get_consul_value("Project", "NAME") or "DjangoStartKit"
    DEBUG = get_consul_value("Project", "DEBUG") or False
    ENVIRONMENT = get_consul_value("Project", "ENVIRONMENT") or Environment.production.value
    DESCRIPTION = get_consul_value("Project", "DESCRIPTION") or "Django-start-kit"
    LANGUAGE_CODE = get_consul_value("Project", "LANGUAGE_CODE") or "zh-hans"
    TIME_ZONE = get_consul_value("Project", "TIME_ZONE") or "Asia/Shanghai"
    USE_TZ = get_consul_value("Project", "USE_TZ") or False
    BASE_DIR = BASE_DIR


class Hbase:
    SERVERS = get_consul_value("Hbase", "SERVERS") or []


class Kafka:
    SERVERS = get_consul_value("Kafka", "SERVERS") or []


class Jwt:
    SECRET = get_consul_value("Jwt", "SECRET")
    AUTH_HEADER_PREFIX = get_consul_value("Jwt", "AUTH_HEADER_PREFIX") or "JWT"
    EXPIRATION_DELTA_MINUTES = get_consul_value("Jwt", "EXPIRATION_DELTA_MINUTES") or 432000
    REFRESH_EXPIRATION_DELTA_DELTA_MINUTES = get_consul_value("Jwt", "REFRESH_EXPIRATION_DELTA_DELTA_MINUTES") or 4320


class K8s:
    HOST = get_consul_value("K8s", "HOST")
    PORT = get_consul_value("K8s", "PORT")
    NAMESPACE = get_consul_value("K8s", "NAMESPACE")
    IMAGE = get_consul_value("K8s", "IMAGE")
    PVC_NAME = get_consul_value("K8s", "PVC_NAME")
    CONFIG_FILE = get_consul_value("K8s", "CONFIG_FILE")
    CONFIG_MAP_NAME = get_consul_value("K8s", "CONFIG_MAP_NAME")


class LocalConfig:
    """
    全部的配置信息
    """

    YAML_CONFIG = json_config

    PROJECT = Project

    SERVER = Server

    RELATIONAL_DB = RelationalDb

    REDIS = Redis

    OSS = Oss

    JWT = Jwt

    HBASE = Hbase

    KAFKA = Kafka  # noqa

    K8S = K8s

    @property
    def DATABASES(self) -> dict:
        return {
            "default": {
                "ENGINE": "django.db.backends.mysql",
                "NAME": self.RELATIONAL_DB.DB,
                "USER": self.RELATIONAL_DB.USERNAME,
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


@lru_cache()
def get_local_configs() -> LocalConfig:
    return LocalConfig()


local_configs: LocalConfig = get_local_configs()
