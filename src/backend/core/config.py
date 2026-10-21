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
    API_V2_PREFIX: str = "/api"

    # Banco de dados (PostgreSQL padrão como no seu database.py)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/smartparking"

    # JWT e Segurança (com a sua SECRET_KEY padrão)
    SECRET_KEY: str = "sua_chave_secreta_de_producao_aqui"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Hosts aceitos pelo TrustedHostMiddleware (só vale com ENVIRONMENT=production).
    # Wildcards fnmatch funcionam; os padrões abaixo cobrem localhost, IP da LAN
    # (banca/presentação) e containers na rede interna do Docker. Em produção com
    # domínio próprio, acrescente via .env:
    # TRUSTED_HOSTS='["meudominio.com","localhost","192.168.*.*"]'
    TRUSTED_HOSTS: List[str] = [
        "localhost",
        "127.0.0.1",
        "host.docker.internal",
        "192.168.*.*",
        "10.*.*.*",
        "172.*.*.*",
    ]

    # Chave de assinatura de requisições anti-replicação (deve ser a MESMA no frontend)
    APP_SIGNING_SECRET: str = "smartparking_default_signing_key_change_in_production"

    # Simulador de sensores: base do app Expo usado para montar a URL do QR
    SIMULADOR_BASE_URL: str = "http://localhost:8081"

    # Popular o banco com os shoppings demo de Manaus ao iniciar (só em DEBUG e com banco vazio)
    SEED_DEMO_ON_STARTUP: bool = True

    # Rede do uvicorn (python main.py): mude com PORT=8010 no .env quando a 8000 estiver ocupada
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # true: se o PostgreSQL estiver fora do ar, cai para SQLite de dev (.smartparking.db).
    # Em time, deixe false para o erro aparecer na cara — evita "dados fantasmas" no SQLite
    DB_AUTO_SQLITE: bool = True

    # OAuth Providers (autenticação social)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    FACEBOOK_CLIENT_ID: Optional[str] = None
    FACEBOOK_CLIENT_SECRET: Optional[str] = None
    APPLE_CLIENT_ID: Optional[str] = None
    APPLE_CLIENT_SECRET: Optional[str] = None


settings = Settings()
