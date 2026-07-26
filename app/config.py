"""Configuração do processo — exclusivamente por variável de ambiente.

`DATABASE_URL` não tem valor padrão: sua ausência impede a partida (TRD).
"""

from functools import lru_cache

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str
    log_level: str = "INFO"
    app_version: str = "0.0.0-dev"
    app_commit: str = "unknown"
    app_timezone: str = "America/Sao_Paulo"


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()  # type: ignore[call-arg]  # campos vêm do ambiente
    except ValidationError as exc:
        raise RuntimeError(
            "configuração inválida: DATABASE_URL é obrigatória e não tem valor "
            f"padrão. Detalhe: {exc}"
        ) from exc
