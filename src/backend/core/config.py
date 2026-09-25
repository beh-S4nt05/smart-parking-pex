from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações centrais da aplicação, carregadas do .env"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Configurações gerais da API
    APP_NAME: str = "SmartParking API"
    APP_DESCRIPTION: str = "Backend em FastAPI para gerenciamento inteligente de vagas"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api"

    # Banco de dados (PostgreSQL padrão como no seu database.py)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/smartparking"

    # JWT e Segurança (com a sua SECRET_KEY padrão)
    SECRET_KEY: str = "sua_chave_secreta_de_producao_aqui"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Chave de assinatura de requisições anti-replicação (deve ser a MESMA no frontend)
    APP_SIGNING_SECRET: str = "smartparking_default_signing_key_change_in_production"

    # OAuth Providers (autenticação social)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    FACEBOOK_CLIENT_ID: Optional[str] = None
    FACEBOOK_CLIENT_SECRET: Optional[str] = None
    APPLE_CLIENT_ID: Optional[str] = None
    APPLE_CLIENT_SECRET: Optional[str] = None


settings = Settings()
