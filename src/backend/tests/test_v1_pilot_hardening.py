"""PR64: hardened pilot rejects demo secrets without changing normal QA mode."""
import pytest
from pydantic import ValidationError

from core.config import Settings


def _piloto(**overrides):
    dados = {
        "SECURITY_PILOT_HARDENED": True,
        "ENVIRONMENT": "staging",
        "SECRET_KEY": "segredo-exclusivo-com-mais-de-trinta-e-dois-bytes",
        "DATABASE_URL": "postgresql+psycopg2://postgres:senha%40exclusiva%231234@postgres:5432/smartparking",
        "APP_SIGNING_SECRET": "not-used-for-authorization-client-bundled",
    }
    dados.update(overrides)
    return Settings(_env_file=None, **dados)


def test_piloto_protegido_aceita_credenciais_nao_padrao():
    settings = _piloto()
    assert settings.SECURITY_PILOT_HARDENED is True


@pytest.mark.parametrize("field,value", [
    ("SECRET_KEY", "mude_efta_chave_secreta_em_producao"),
    ("SECRET_KEY", "abc"),
    ("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@postgres:5432/smartparking"),
    ("DATABASE_URL", "postgresql+psycopg2://postgres:123@postgres:5432/smartparking"),
])
def test_piloto_rejeita_segundos_de_demonstracao(field, value):
    with pytest.raises(ValidationError):
        _piloto(**{field: value})


def test_desenvolvimento_mantem_valores_legados_sem_ativar_modo_protegido():
    settings = Settings(_env_file=None, ENVIRONMENT="staging",
                        SECURITY_PILOT_HARDENED=False,
                        SECRET_KEY="mude_efta_chave_secreta_em_producao")
    assert settings.SECURITY_PILOT_HARDENED is False
