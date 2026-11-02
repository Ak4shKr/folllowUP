from dataclasses import dataclass
from urllib.parse import quote_plus

from app.core.env import env


@dataclass(frozen=True, slots=True)
class AppConfig:
    name: str
    version: str
    environment: str
    log_level: str
    require_email_approval: bool


@dataclass(frozen=True, slots=True)
class ApiConfig:
    host: str
    port: int


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    async_url: str
    sync_url: str
    pool_size: int
    max_overflow: int
    pool_timeout: int
    echo: bool


def build_url(driver: str) -> str:
    """Build a Postgres URL, escaping the user and password."""
    user = quote_plus(env.pg_user)
    password = quote_plus(env.pg_password.get_secret_value())
    return f"postgresql+{driver}://{user}:{password}@{env.pg_host}:{env.pg_port}/{env.pg_database}"


api = ApiConfig(
    host=env.api_bind_host,
    port=env.api_bind_port,
)

database = DatabaseConfig(
    async_url=build_url("asyncpg"),
    sync_url=build_url("psycopg"),
    pool_size=env.pg_pool_size,
    max_overflow=env.pg_max_overflow,
    pool_timeout=env.pg_pool_timeout,
    echo=env.pg_echo,
)

settings = AppConfig(
    name=env.app_name,
    version=env.app_version,
    environment=env.app_env,
    log_level=env.log_level,
    require_email_approval=env.require_email_approval,
)
