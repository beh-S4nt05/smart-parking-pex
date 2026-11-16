"""Entrega de identidade PR60: SMTP verificado, desafios descartáveis e TOTP cifrado."""
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import smtplib

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.config import settings
from core.identity_security import gerar_token_uso_unico, hash_token, novo_segredo_totp, uri_totp, validar_totp
from core.security import criar_hash_senha, verificar_senha
from models.db_models import RevogacaoToken, TokenIdentidade, Usuario

PAPEIS_MFA = frozenset({"admin", "gestor", "financeiro"})


def _fernet() -> Fernet:
    if not settings.MFA_ENCRYPTION_KEY:
        raise HTTPException(status_code=503, detail="MFA requer chave de criptografia configurada no servidor")
    try:
        return Fernet(settings.MFA_ENCRYPTION_KEY.encode("ascii"))
    except (ValueError, TypeError):
        raise HTTPException(status_code=503, detail="Chave de MFA inválida no servidor") from None


def _descriptografar(cifrado: str) -> str:
    try:
        return _fernet().decrypt(cifrado.encode("ascii")).decode("ascii")
    except InvalidToken:
        raise HTTPException(status_code=503, detail="Segredo MFA não pôde ser validado no servidor") from None


def iniciar_mfa(db: Session, usuario: Usuario, senha_atual: str) -> dict:
    if usuario.role not in PAPEIS_MFA:
        raise HTTPException(status_code=403, detail="MFA obrigatório nesta etapa apenas para equipe de gestão")
    if not verificar_senha(senha_atual, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Senha atual incorreta")
    if usuario.mfa_ativado_em:
        raise HTTPException(status_code=409, detail="MFA já está ativo nesta conta")
    segredo = novo_segredo_totp()
    usuario.mfa_segredo_cifrado = _fernet().encrypt(segredo.encode("ascii")).decode("ascii")
    usuario.mfa_ultimo_contador = -1
    db.commit()
    # O QR/URI só é fornecido durante a configuração autenticada, nunca no login.
    return {"uri_totp": uri_totp(segredo, usuario.email)}


def validar_codigo_usuario(db: Session, usuario: Usuario, codigo: str, *, persistir: bool = True) -> bool:
    if not usuario.mfa_segredo_cifrado:
        return False
    segredo = _descriptografar(usuario.mfa_segredo_cifrado)
    contador = validar_totp(segredo, codigo, ultimo_contador=usuario.mfa_ultimo_contador)
    if contador is None:
        return False
    if persistir:
        usuario.mfa_ultimo_contador = contador
        db.commit()
    return True


def confirmar_mfa(db: Session, usuario: Usuario, codigo: str) -> None:
    if not usuario.mfa_segredo_cifrado or usuario.mfa_ativado_em:
        raise HTTPException(status_code=409, detail="MFA não está aguardando confirmação")
    if not validar_codigo_usuario(db, usuario, codigo):
        raise HTTPException(status_code=401, detail="Código MFA inválido")
    usuario.mfa_ativado_em = datetime.now(timezone.utc)
    db.commit()


def exigir_mfa_no_login(db: Session, usuario: Usuario, codigo: str | None) -> None:
    if usuario.role not in PAPEIS_MFA:
        return
    if settings.SECURITY_STAFF_MFA_REQUIRED and not usuario.mfa_ativado_em:
        raise HTTPException(status_code=403, detail="MFA não ativado para esta conta de equipe. Solicite a configuração ao administrador.")
    if not usuario.mfa_ativado_em:
        return
    if not codigo or not validar_codigo_usuario(db, usuario, codigo):
        raise HTTPException(status_code=401, detail="Código MFA ausente, expirado ou inválido")


def _smtp_disponivel() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_SENDER)


def _enviar_email(destino: str, titulo: str, corpo: str) -> None:
    if not _smtp_disponivel():
        raise HTTPException(status_code=503, detail="Serviço de e-mail não configurado para envio de códigos")
    msg = EmailMessage()
    msg["From"] = settings.SMTP_SENDER
    msg["To"] = destino
    msg["Subject"] = titulo
    msg.set_content(corpo)
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=8) as servidor:
            if settings.SMTP_STARTTLS:
                servidor.starttls()
            if settings.SMTP_USER:
                servidor.login(settings.SMTP_USER, settings.SMTP_PASSWORD or "")
            servidor.send_message(msg)
    except (OSError, smtplib.SMTPException):
        raise HTTPException(status_code=503, detail="Falha temporária de entrega de e-mail") from None


def solicitar_desafio(db: Session, email: str, finalidade: str) -> None:
    if finalidade not in {"verificar_email", "recuperar_senha"}:
        raise ValueError("finalidade inválida")
    # Fail closed e sem gerar token se não existe transportador de e-mail.
    if not _smtp_disponivel():
        raise HTTPException(status_code=503, detail="Serviço de e-mail não configurado")
    usuario = db.query(Usuario).filter(Usuario.email == email.strip().lower()).first()
    if not usuario or not usuario.is_ativo:
        return  # resposta idêntica para evitar enumeração
    if finalidade == "verificar_email" and usuario.email_verificado_em:
        return
    token, digest = gerar_token_uso_unico()
    desafio = TokenIdentidade(
        usuario_id=usuario.id, finalidade=finalidade, token_hash=digest,
        expira_em=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    db.add(desafio)
    db.flush()
    assunto = "Smart Parking - confirmação de e-mail" if finalidade == "verificar_email" else "Smart Parking - recuperação de senha"
    _enviar_email(usuario.email, assunto, f"Código de uso único (15 minutos): {token}\nNão compartilhe esse código.")
    db.commit()


def consumir_desafio(db: Session, token: str, finalidade: str) -> Usuario:
    agora = datetime.now(timezone.utc)
    row = db.query(TokenIdentidade).filter(
        TokenIdentidade.token_hash == hash_token(token),
        TokenIdentidade.finalidade == finalidade,
    ).with_for_update().first()
    if not row or row.consumido_em:
        raise HTTPException(status_code=400, detail="Código inválido ou já utilizado")
    expira = row.expira_em
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=timezone.utc)
    if agora >= expira:
        raise HTTPException(status_code=400, detail="Código expirado")
    usuario = db.get(Usuario, row.usuario_id)
    if not usuario or not usuario.is_ativo:
        raise HTTPException(status_code=400, detail="Código inválido")
    row.consumido_em = agora
    db.flush()
    return usuario


def confirmar_email(db: Session, token: str) -> None:
    usuario = consumir_desafio(db, token, "verificar_email")
    usuario.email_verificado_em = datetime.now(timezone.utc)
    db.commit()


def redefinir_senha(db: Session, token: str, nova_senha: str) -> None:
    usuario = consumir_desafio(db, token, "recuperar_senha")
    usuario.senha_hash = criar_hash_senha(nova_senha)
    db.add(RevogacaoToken(jti=None, usuario_id=usuario.id, motivo="recuperacao_senha",
                          criado_em=datetime.now(timezone.utc)))
    db.commit()
