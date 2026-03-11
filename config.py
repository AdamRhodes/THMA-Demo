from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Salesforce
    sf_username: str = ""
    sf_password: str = ""
    sf_security_token: str = ""
    sf_client_id: str = ""
    sf_client_secret: str = ""
    sf_domain: str = "login"

    # Azure SQL
    azure_sql_server: str = ""
    azure_sql_database: str = "thma-demo"
    azure_sql_username: str = ""
    azure_sql_password: str = ""

    # API
    api_key: str = "change-me-to-a-strong-random-key"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Demo mode: use SQLite instead of Azure SQL
    demo_mode: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def azure_sql_connection_string(self) -> str:
        return (
            f"mssql+pyodbc://{quote_plus(self.azure_sql_username)}:{quote_plus(self.azure_sql_password)}"
            f"@{self.azure_sql_server}/{self.azure_sql_database}"
            f"?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no"
        )

    @property
    def database_url(self) -> str:
        if self.demo_mode:
            return "sqlite:///demo.db"
        return self.azure_sql_connection_string


@lru_cache
def get_settings() -> Settings:
    return Settings()