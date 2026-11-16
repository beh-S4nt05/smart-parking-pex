import re

import jwt as pyjwt
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.security import (
    criar_hash_senha,
    criar_token,
    decodificar_token,
    verificar_senha,
)
from models.db_models import CredencialEstacionamento, Usuario, Veiculo
from models.schemas import LoginRequest, TokenResponse, UsuarioCreate, UsuarioResponse


def _somente_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def buscar_usuario_por_credencial(db: Session, credencial: str) -> Usuario | None:
    """
    Localiza um usuário pelo e-mail OU telefone.
    - Se a credencial contém "@" -> busca por e-mail (case-insensitive).
    - Caso contrário -> compara apenas os dígitos do telefone cadastrado.
    """
    credencial = (credencial or "").strip()
    if not credencial:
        return None

    if "@" in credencial:
        return (
            db.query(Usuario)
            .filter(func.lower(Usuario.email) == credencial.lower())
            .first()
        )

    digitos = _somente_digitos(credencial)
    if len(digitos) < 8:
        return None

    # Escala pequena (demo/piloto): normalizar em Python é mais simples e
    # portável do que SQL de regexp por banco.
    for usuario in db.query(Usuario).filter(Usuario.telefone.isnot(None)).all():
        if _somente_digitos(usuario.telefone) == digitos:
            return usuario
    return None


def criar_usuario(db: Session, dados: UsuarioCreate) -> Usuario:
    """Cria um novo usuário com senha hasheada"""
    email = (dados.email or "").strip().lower()
    usuario_existente = db.query(Usuario).filter(Usuario.email == email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-mail já cadastrado no sistema"
        )

    senha_hash = criar_hash_senha(dados.senha)
    novo_usuario = Usuario(
        nome=dados.nome.strip(),
        email=email,
        telefone=_somente_digitos(dados.telefone) if dados.telefone else None,
        placa_veiculo=(dados.placa_veiculo or "").upper().replace(" ", "") or None,
        senha_hash=senha_hash,
        role="usuario",  # Usuários cadastrados publicamente são sempre comuns
        is_ativo=True,
        is_pcd=dados.is_pcd,  # campo legado: solicitação de credencial não concede elegibilidade
        data_nascimento=dados.data_nascimento,
    )

    db.add(novo_usuario)
    db.flush()  # gerar id do novo usuário; gravar usuário, veículo e solicitação na mesma transação
    if dados.veiculo:
        db.add(Veiculo(
            usuario_id=novo_usuario.id,
            placa=dados.veiculo.placa,
            categoria=dados.veiculo.categoria,
            motorizacao=dados.veiculo.motorizacao,
            modelo=dados.veiculo.modelo,
            principal=True,
        ))
        novo_usuario.placa_veiculo = dados.veiculo.placa
    if dados.beneficio_solicitado:
        db.add(CredencialEstacionamento(
            usuario_id=novo_usuario.id,
            tipo=dados.beneficio_solicitado,
            status="pendente",  # exige verificação oficial posterior; não libera a vaga
        ))
    db.commit()
    db.refresh(novo_usuario)
    return novo_usuario


def montar_token_response(usuario: Usuario, access: str, refresh: str) -> TokenResponse:
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        user=UsuarioResponse.model_validate(usuario),
    )


def autenticar_usuario(db: Session, dados: LoginRequest, agente: str | None = None) -> TokenResponse:
    """
    Autentica usuário por e-mail OU telefone e retorna access + refresh tokens
    + os dados do usuário (o app usa `user` para popular o AuthContext).
    """
    credencial = (dados.email or "").strip()
    if "@" in credencial:
        usuario = buscar_usuario_por_credencial(db, credencial)
        senha_correta = bool(usuario and verificar_senha(dados.senha, usuario.senha_hash))
    else:
        # Telefones não possuem restrição de unicidade no banco.
        # A implementação antiga devolvia o PRIMEIRO usuário com o número,
        # ignorando a senha dos demais. Isso bloqueava o login de contas
        # cadastradas que compartilhassem um telefone.
        digitos = _somente_digitos(credencial)
        candidatos = (
            [u for u in db.query(Usuario).filter(Usuario.telefone.isnot(None)).all()
             if _somente_digitos(u.telefone) == digitos]
            if len(digitos) >= 8 else []
        )
        correspondentes = [
            u for u in candidatos if verificar_senha(dados.senha, u.senha_hash)
        ]
        if len(correspondentes) > 1:
            # Duas contas compartilham telefone E senha: nenhuma pode ser
            # escolhida sem identificar a conta. Nunca escolher arbitrariamente.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Mais de uma conta corresponde ao telefone informado. Entre usando seu e-mail.",
            )
        usuario = correspondentes[0] if correspondentes else None
        senha_correta = usuario is not None

    if not senha_correta:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail/telefone ou senha incorretos",
        )

    if not usuario.is_ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado. Contate o suporte."
        )

    from core.config import settings
    from rules import identity_service

    if settings.SECURITY_VERIFIED_EMAIL_REQUIRED and not usuario.email_verificado_em:
        raise HTTPException(status_code=403, detail="Confirme o e-mail cadastrado antes de entrar")
    identity_service.exigir_mfa_no_login(db, usuario, dados.mfa_codigo)

    from rules import session_service
    access_token, refresh_token = session_service.iniciar(db, usuario, agente)

    return montar_token_response(usuario, access_token, refresh_token)


def renovar_access_token(db: Session, refresh_token: str) -> TokenResponse:
    """
    Renova o access token usando um refresh token válido e retorna também o
    refresh_token atual (mantido o mesmo para não invalidar outras sessões).
    """
    try:
        payload = decodificar_token(refresh_token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expirado")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Tipo de token incorreto")

    usuario_id = payload.get("sub")
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    if not usuario.is_ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado. Contate o suporte.",
        )

    # RF-13: o refresh pode estar vivo na assinatura e MORTO em revogação
    # (logout revogou a cadeia; troca de senha marcou o usuário inteiro).
    from core.deps import sessao_revogada

    if sessao_revogada(db, payload, usuario_id):
        raise HTTPException(status_code=401, detail="Sessão encerrada. Faça login novamente.")

    if payload.get("sid"):
        from rules import session_service
        novo_access, novo_refresh = session_service.renovar(db, usuario, payload)
    else:
        # Compatibilidade durante migração: tokens antigos sem sid expiram
        # naturalmente. PR64 pode tornar SECURITY_SESSIONS_REQUIRED obrigatório.
        novo_access = criar_token(subject=usuario_id, tipo_token="access")
        novo_refresh = refresh_token
    return montar_token_response(usuario, novo_access, novo_refresh)
