from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(BaseSettings):
    """Raw values from .env. The only file that reads the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "flwUp"
    app_version: str = "0.1.0"
    app_env: str = "development"
    log_level: str = "INFO"

    api_bind_host: str = "127.0.0.1"
    api_bind_port: int = 8000

    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_user: str = "postgres"
    pg_password: SecretStr
    pg_database: str = "flwup"
    pg_pool_size: int = 5
    pg_max_overflow: int = 10
    pg_pool_timeout: int = 30
    pg_echo: bool = False

    require_email_approval: bool = True

    google_sheet_id: str = ""
    google_sheet_range: str = "Contacts!A:H"
    google_credentials_file: str = ""
    google_field_mapping: str = (
        "email=email,name=name,company_name=company_name,designation=designation,"
        "company_website=company_website,target_role=target_role,source=source,mobile=mobile"
    )


env = Env()  # type: ignore[call-arg]  # values come from .env / environment
