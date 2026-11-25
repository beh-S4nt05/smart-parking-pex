"""Autorização UMA VEZ da conta Gmail empresarial via OAuth 2.0.

Executar no Linux do operador, nunca no APK nem numa rota pública.
O navegador usa somente loopback 127.0.0.1 e o escopo gmail.send.
Grava os tokens no .env.piloto privado (permissões 0600), sem imprimir
refresh token, client secret ou códigos OAuth no terminal.

Exemplo:
 python src/backend/piloto_autorizar_gmail.py \
   --client-json ~/Downloads/client_secret_....json \
   --env-file src/.env.piloto --remetente conta@gmail.com
"""
import argparse
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import tempfile
import time
from urllib.parse import parse_qs, urlencode, urlparse
import webbrowser

import httpx

ESCOPO = "https://www.googleapis.com/auth/gmail.send"
AUTORIZACAO = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"


def _salvar_env_privado(caminho: Path, novos: dict[str, str]) -> None:
    """Preserva toda a configuração existente e substitui só campos Gmail."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    original = caminho.read_text(encoding="utf-8") if caminho.exists() else ""
    linhas = original.splitlines()
    resultado = []
    gravados = set()
    for linha in linhas:
        chave = linha.split("=", 1)[0].strip()
        if not linha.lstrip().startswith("#") and chave in novos:
            if chave not in gravados:
                resultado.append(f"{chave}={json.dumps(novos[chave])}")
                gravados.add(chave)
        else:
            resultado.append(linha)
    for chave, valor in novos.items():
        if chave not in gravados:
            resultado.append(f"{chave}={json.dumps(valor)}")

    # Arquivo temporário no mesmo diretório: replace atômico e modo 0600.
    fd, temporario = tempfile.mkstemp(prefix=".gmail-oauth-", dir=caminho.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
            arquivo.write("\n".join(resultado).rstrip() + "\n")
        os.chmod(temporario, 0o600)
        os.replace(temporario, caminho)
    finally:
        if os.path.exists(temporario):
            os.unlink(temporario)


def _ler_cliente_oauth(caminho: Path) -> tuple[str, str, str, list[str]]:
    """Aceita os JSONs reais emitidos pelo Google Cloud: installed e web.

    O nome do arquivo é irrelevante. NÃO imprimir IDs, segredos ou tokens.
    """
    try:
        dados = json.loads(caminho.expanduser().read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError("Arquivo JSON não encontrado no caminho informado") from None
    except OSError:
        raise ValueError("Não foi possível ler o JSON informado") from None
    except json.JSONDecodeError:
        raise ValueError("O arquivo informado não contém JSON válido") from None

    if not isinstance(dados, dict):
        raise ValueError("A raiz do JSON OAuth precisa ser um objeto")
    if isinstance(dados.get("installed"), dict):
        tipo, cred = "desktop", dados["installed"]
    elif isinstance(dados.get("web"), dict):
        tipo, cred = "web", dados["web"]
    elif isinstance(dados.get("client_id"), str) and isinstance(dados.get("client_secret"), str):
        # Alguns exportadores entregam as duas chaves no nível superior.
        tipo, cred = "web", dados
    elif dados.get("type") == "service_account":
        raise ValueError(
            "O arquivo é uma conta de serviço, não um cliente OAuth de usuário. "
            "Para Gmail pessoal é necessário OAuth com consentimento da conta remetente."
        )
    else:
        raise ValueError(
            "JSON válido, mas sem client_id e client_secret na estrutura OAuth. "
            "Aceitos: chaves 'installed', 'web' ou credenciais na raiz."
        )
    client_id, client_secret = cred.get("client_id"), cred.get("client_secret")
    if not isinstance(client_id, str) or not client_id.strip():
        raise ValueError("JSON OAuth sem client_id válido")
    if not isinstance(client_secret, str) or not client_secret.strip():
        raise ValueError("JSON OAuth sem client_secret válido")

    uris = cred.get("redirect_uris", [])
    if not isinstance(uris, list):
        uris = []
    return tipo, client_id, client_secret, [u for u in uris if isinstance(u, str)]


def _validar_callback_local(uri: str) -> tuple[str, int, str]:
    """Não aceitar callback remoto: o script recebe códigos somente em loopback."""
    try:
        parsed = urlparse(uri)
        port = parsed.port
    except ValueError:
        raise ValueError("Porta do redirect_uri inválida") from None
    if (parsed.scheme != "http"
            or parsed.hostname not in ("127.0.0.1", "localhost")
            or not port or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        raise ValueError(
            "Use redirect_uri HTTP local com porta fixa, por exemplo "
            "http://127.0.0.1:8765/oauth/callback"
        )
    return parsed.hostname, port, parsed.path or "/"


def _redirect_web(uris: list[str], fornecida: str | None) -> str:
    """Web OAuth exige URI registrado EXATAMENTE no Google Cloud."""
    if fornecida:
        _validar_callback_local(fornecida)
        return fornecida

    for uri in uris:
        try:
            _validar_callback_local(uri)
        except ValueError:
            continue
        return uri

    raise ValueError(
        "JSON do tipo 'web' reconhecido, mas sem redirect_uri local autorizado. "
        "No Google Cloud > APIs e serviços > Credenciais > cliente OAuth Web, "
        "adicione 'http://127.0.0.1:8765/oauth/callback' em URIs de "
        "redirecionamento autorizados. Depois execute com "
        "--redirect-uri http://127.0.0.1:8765/oauth/callback "
        "(não precisa renomear nem recriar o JSON)."
    )


def _iniciar_servidor_callback(porta: int = 0, rota: str = "/oauth/callback"):

    estado = {}
    class Callback(BaseHTTPRequestHandler):
        def log_message(self, formato, *args):
            pass  # Nunca registrar authorization code na URL.
        def do_GET(self):
            if urlparse(self.path).path != rota:
                self.send_error(404)
                return
            params = parse_qs(urlparse(self.path).query)
            estado["params"] = params
            sucesso = bool(params.get("code")) and not params.get("error")
            mensagem = (
                "Autorização recebida. Volte ao terminal para concluir."
                if sucesso else "Não foi possível autorizar a conta. Volte ao terminal."
            )
            self.send_response(200 if sucesso else 400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write((
                "<!doctype html><html lang='pt-BR'><meta charset='utf-8'>"
                "<title>Smart Parking — Gmail</title>"
                "<body style='font:16px sans-serif;padding:40px'>"
                f"<h2>{mensagem}</h2></body></html>"
            ).encode("utf-8"))
    servidor = HTTPServer(("127.0.0.1", porta), Callback)
    return servidor, estado


def main() -> int:
    parser = argparse.ArgumentParser(description="Autorizar Gmail API para o Smart Parking")
    parser.add_argument("--client-json", type=Path, required=True,
                        help="Caminho para o JSON OAuth do Google Cloud, seja web ou desktop")
    parser.add_argument("--env-file", type=Path, default=Path("src/.env.piloto"))
    parser.add_argument("--remetente", required=True,
                        help="Endereço Gmail autorizado ou alias verificado")
    parser.add_argument("--redirect-uri", default=None,
                        help="Somente para cliente Web: URI local EXATO registrado no Google Cloud")
    args = parser.parse_args()
    if "@" not in args.remetente or any(x in args.remetente for x in "\r\n"):
        parser.error("Informe apenas o e-mail remetente, sem nome de exibição")
    try:
        tipo, client_id, client_secret, uris = _ler_cliente_oauth(args.client_json)
        if tipo == "web":
            redirect = _redirect_web(uris, args.redirect_uri)
            _, porta, rota = _validar_callback_local(redirect)
            print("Cliente OAuth Web reconhecido; usando callback local registrado:", redirect)
        else:
            if args.redirect_uri:
                parser.error("--redirect-uri é exclusivo de clientes OAuth do tipo Web")
            porta, rota = 0, "/oauth/callback"
            print("Cliente OAuth Desktop reconhecido; usando callback local dinâmico.")
        servidor, recebido = _iniciar_servidor_callback(porta=porta, rota=rota)
    except ValueError as exc:
        parser.error(str(exc))
    except OSError:
        parser.error(
            "Não foi possível abrir a porta do callback local. "
            "Verifique se já existe outro programa usando a porta configurada."
        )
    if tipo == "desktop":
        redirect = f"http://127.0.0.1:{servidor.server_port}/oauth/callback"
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    url = AUTORIZACAO + "?" + urlencode({
        "client_id": client_id, "redirect_uri": redirect,
        "response_type": "code", "scope": ESCOPO, "access_type": "offline",
        "prompt": "consent", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
    })

    print("Abrindo o navegador para autorizar SOMENTE o envio de e-mails.")
    print("Confira a conta Google escolhida. Não envie tokens nem credenciais a terceiros.")
    if not webbrowser.open(url):
        print("Acesse no navegador deste computador:", url)
    servidor.timeout = 2
    prazo = time.monotonic() + 300
    try:
        while "params" not in recebido and time.monotonic() < prazo:
            servidor.handle_request()
    finally:
        servidor.server_close()
    params = recebido.get("params", {})
    if params.get("state", [""])[0] != state or not params.get("code"):
        if params.get("error"):
            parser.error("Autorização Google negada. Confira usuário de teste, consentimento e permissões.")
        parser.error("OAuth não autorizado, estado inválido ou callback expirou. Nenhuma credencial foi gravada.")

    try:
        resp = httpx.post(TOKEN, data={
            "code": params["code"][0],
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        }, timeout=15)
        resp.raise_for_status()
        resposta = resp.json()
    except (httpx.HTTPError, ValueError):
        parser.error("Falha ao concluir OAuth no Google. Confira o cliente OAuth, URI de retorno e consentimento.")
    refresh_token = resposta.get("refresh_token")
    escopos = resposta.get("scope", "").split()
    if not isinstance(refresh_token, str) or not refresh_token or ESCOPO not in escopos:
        parser.error("Google não retornou refresh token e escopo gmail.send. Reautorize com consentimento offline.")

    _salvar_env_privado(args.env_file, {
        "EMAIL_PROVIDER": "gmail_api",
        "GMAIL_CLIENT_ID": client_id,
        "GMAIL_CLIENT_SECRET": client_secret,
        "GMAIL_REFRESH_TOKEN": refresh_token,
        "GMAIL_SENDER": args.remetente.strip().lower(),
        # Não ativar confirmação sem smoke de envio real no servidor.
        "SECURITY_VERIFIED_EMAIL_REQUIRED": "false",
    })
    print("OAuth autorizado; credenciais gravadas com permissão 0600 em", args.env_file)
    print("Confirmação obrigatória permanece DESLIGADA até o teste de envio real.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
