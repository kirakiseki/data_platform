import os
from typing import Literal, Type

from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    TomlConfigSettingsSource,
)

YAML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.toml")


class LoggingSettings(BaseModel):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"]
    third_party_libs: list[str]


class DatabaseSettings(BaseModel):
    url: str
    port: int
    username: str
    password: str
    database: str
    health_timeout: int


class ServerSettings(BaseModel):
    root_path: str = ""


class Settings(BaseSettings):
    @classmethod
    def settings_customise_sources(
        cls, settings_cls: Type[BaseSettings], **kwargs
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (TomlConfigSettingsSource(settings_cls, toml_file=YAML_FILE),)

    logging: LoggingSettings
    database: DatabaseSettings
    server: ServerSettings = ServerSettings()


SETTINGS = Settings()
