"""TOTP RFC 6238 (SHA-1) e tokens de uso único para V1.

Nada aqui supõe confiança no cliente. Segredos TOTP não devem ser retornados
depois da configuração e precisam ser criptografados em repouso antes de
habilitar o recurso para contas reais.
"""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote


def novo_segredo_totp() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _hotp(segredo: str, contador: int) -> str:
    chave = base64.b32decode(segredo.upper() + "=" * (-len(segredo) % 8))
    digesto = hmac.new(chave, struct.pack(">Q", contador), hashlib.sha1).digest()
    deslocamento = digesto[-1] & 0x0F
    valor = struct.unpack(">I", digesto[deslocamento:deslocamento + 4])[0] & 0x7FFFFFFF
    return f"{valor % 1000000:06d}"


def validar_totp(segredo: str, codigo: str, *, agora: int | None = None,
                  ultimo_contador: int = -1, tolerancia: int = 1) -> int | None:
    """Retorna contador aceito ou None; o chamador persiste o contador para impedir replay."""
    if not isinstance(codigo, str) or len(codigo) != 6 or not codigo.isascii() or not codigo.isdecimal():
        return None
    momento = int(time.time() if agora is None else agora)
    corrente = momento // 30
    for contador in range(max(0, corrente - tolerancia), corrente + tolerancia + 1):
        if contador > ultimo_contador and hmac.compare_digest(_hotp(segredo, contador), codigo):
            return contador
    return None


def uri_totp(segredo: str, email: str) -> str:
    issuer = "Smart Parking"
    return (f"otpauth://totp/{quote(issuer + ':' + email, safe='')}?"
            f"secret={segredo}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30")


def gerar_token_uso_unico() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode("ascii")).hexdigest()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()



def gerar_codigo_email() -> str:
    """Código curto de 6 dígitos, gerado com CSPRNG para confirmação no app."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_codigo_email(email: str, codigo: str) -> str:
    """HMAC de código curto: o vazamento do banco não permite testar 10^6 combinações offline."""
    from core.config import settings
    chave = settings.APP_SIGNING_SECRET.encode("utf-8")
    mensagem = f"verificar_email:{email.strip().lower()}:{codigo}".encode("utf-8")
    return hmac.new(chave, mensagem, hashlib.sha256).hexdigest()
