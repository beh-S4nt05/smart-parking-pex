
from pydantic import model_validator
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

    # Segurança — janela anti-duplicidade do middleware (produção): POSTs/PUTs
    # idênticos da MESMA origem em <1s recebem 429. Desligado por padrão para
    # não estrangular integrações legítimas em rajada; ligue no .env.
    BLOQUEIO_DUPLICIDADE: bool = False

    # Banco de dados (PostgreSQL padrão como no seu database.py).
    # Driver EXPLÍCITO psycopg2: sem o sufixo, SQLAlchemy>=2.1 procura o
    # psycopg v3 (não instalado) e o app "cai" no SQLite achando que o
    # Postgres morreu. Se trocar para psycopg[binary], use +psycopg.
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/smartparking"

    # JWT e Segurança (com a sua SECRET_KEY padrão)
    SECRET_KEY: str = "sua_chave_secreta_de_producao_aqui"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # None = origens locais apenas em desenvolvimento; lista vazia em produção.
    # Uma lista explícita sempre prevalece. Nunca usamos curinga com credenciais.
    CORS_ORIGINS: list[str] | None = None
    CORS_ORIGIN_REGEX: str | None = None

    # Hosts aceitos pelo TrustedHostMiddleware (só vale com ENVIRONMENT=production).
    # Wildcards fnmatch funcionam; os padrões abaixo cobrem localhost, IP da LAN
    # (banca/presentação) e containers na rede interna do Docker. Em produção com
    # domínio próprio, acrescente via .env:
    # TRUSTED_HOSTS='["meudominio.com","localhost","192.168.*.*"]'
    TRUSTED_HOSTS: list[str] = [
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

    # OAuth Providers (autenticação social). ACH-08/ADR-06: o fluxo social
    # tem bugs conhecidos (Apple JWKS/Facebook sem app validation), então as
    # rotas só existem com a flag ligada — desligada, respondem 404.
    LOGIN_SOCIAL_ENABLED: bool = False

    # OAuth Providers (autenticação social)
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    FACEBOOK_CLIENT_ID: str | None = None
    FACEBOOK_CLIENT_SECRET: str | None = None
    APPLE_CLIENT_ID: str | None = None
    APPLE_CLIENT_SECRET: str | None = None

    # ACH-02/ADR-06 (M2-02): o servidor RECUSA subir em produção com as
    # chaves de exemplo — falha no boot é melhor que segredo fraco no ar.
    @model_validator(mode="after")
    def _travar_producao(self):
        if str(self.ENVIRONMENT).lower() == "production":
            if (self.CORS_ORIGINS and "*" in self.CORS_ORIGINS) or self.CORS_ORIGIN_REGEX in {".*", "^.*$"}:
                raise ValueError(
                    "ENVIRONMENT=production não permite CORS curinga; "
                    "declare as origens HTTPS do frontend em CORS_ORIGINS."
                )
            if self.SECRET_KEY == "sua_chave_secreta_de_producao_aqui":
                raise ValueError(
                    "ENVIRONMENT=production exige SECRET_KEY própria no .env "
                    "(a chave de exemplo está bloqueada)."
                )
            if self.APP_SIGNING_SECRET == "smartparking_default_signing_key_change_in_production":
                raise ValueError(
                    "ENVIRONMENT=production exige APP_SIGNING_SECRET própria no .env."
                )
        return self


settings = Settings()
