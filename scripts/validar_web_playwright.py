#!/usr/bin/env python3
"""Valida a versão Web estática com Playwright em Python.

O script é autônomo: prepara um SQLite de QA, sobe o FastAPI de teste na
:8010, serve o bundle estático com proxy same-origin na :8000 e dirige um
Chromium real pela API Python do Playwright. Não usa o runner Node.

Uso típico (após ``expo export --platform web``):

    python scripts/validar_web_playwright.py

Variáveis opcionais:
    UI_WEB_DIST              diretório do export (default: src/frontend/smart-parking/dist)
    UI_PYTHON                Python usado no backend (default: sys.executable)
    UI_API_PORT / UI_WEB_PORT
    UI_DATABASE_PATH
    PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
    PLAYWRIGHT_CHROMIUM_LD_LIBRARY_PATH
    PLAYWRIGHT_CHROMIUM_FONTCONFIG_PATH
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DIST = Path(
    os.environ.get("UI_WEB_DIST", ROOT / "src" / "frontend" / "smart-parking" / "dist")
).resolve()
PYTHON = os.environ.get("UI_PYTHON", sys.executable)
API_PORT = int(os.environ.get("UI_API_PORT", "8010"))
WEB_PORT = int(os.environ.get("UI_WEB_PORT", "8000"))
DB_PATH = Path(os.environ.get("UI_DATABASE_PATH", "/tmp/smartparking-web-validation.db"))
API_URL = f"http://127.0.0.1:{API_PORT}"
BASE_URL = f"http://127.0.0.1:{WEB_PORT}"
RESET_TOKEN = "smart-parking-ui-local-tests"

BACKEND_ENV = {
    **os.environ,
    "ENVIRONMENT": "test",
    "DEBUG": "False",
    "DATABASE_URL": f"sqlite:///{DB_PATH}",
    "DB_AUTO_SQLITE": "False",
    "SEED_DEMO_ON_STARTUP": "False",
    "SECRET_KEY": "ui-tests-secret-key-com-mais-de-32-caracteres",
    "APP_SIGNING_SECRET": "ui-tests-signing-key-com-mais-de-32-caracteres",
    "UI_DATABASE_PATH": str(DB_PATH),
    "UI_API_PORT": str(API_PORT),
    "UI_TEST_RESET_TOKEN": RESET_TOKEN,
}

API_PREFIX = re.compile(
    r"^/(?:api(?:/|$)|auth(?:/|$)|health$|docs(?:/|$)|redoc(?:/|$)|openapi\.json$)"
)


# --------------------------------------------------------------------------
# Servidor Web Python: estático + proxy same-origin para a API de QA
# --------------------------------------------------------------------------
class WebHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args: object) -> None:
        return

    def handle_one_request(self) -> None:  # noqa: N802
        # Conexões fechadas pelo Chrome antes do request chegar não são
        # falha da aplicação; só não devem virar traceback na saída de QA.
        try:
            super().handle_one_request()
        except (ConnectionResetError, BrokenPipeError):
            self.close_connection = True

    def _caminhos_estaticos(self, pathname: str) -> list[Path]:
        limpo = "/index" if pathname == "/" else pathname.rstrip("/")
        relativo = urllib.parse.unquote(limpo).lstrip("/")
        candidatos = [
            DIST / relativo,
            DIST / f"{relativo}.html",
            DIST / relativo / "index.html",
        ]
        # Deep-link de rota dinâmica: o export gera shopping/[id].html.
        if re.fullmatch(r"shopping/[^/]+", relativo):
            candidatos.append(DIST / "shopping" / "[id].html")
        # 404 real em vez de index.html (evita React #418 na tela de rota
        # inexistente e mantém o conteúdo "Unmatched Route" visível).
        candidatos.append(DIST / "+not-found.html")
        return candidatos

    def _responder_arquivo(self, metodo: str, arquivo: Path) -> None:
        dados = arquivo.read_bytes()
        tipo, _ = mimetypes.guess_type(str(arquivo))
        self.send_response(200)
        self.send_header("Content-Type", tipo or "application/octet-stream")
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if metodo != "HEAD":
            self.wfile.write(dados)

    def _servir_estatico(self, metodo: str) -> None:
        pathname = urllib.parse.urlparse(self.path).path
        for candidato in self._caminhos_estaticos(pathname):
            try:
                resolvido = candidato.resolve()
            except OSError:
                continue
            if not resolvido.is_relative_to(DIST) or not resolvido.is_file():
                continue
            self._responder_arquivo(metodo, resolvido)
            return
        self.send_error(404, "Arquivo não encontrado")

    def _proxy(self, metodo: str) -> None:
        tamanho = int(self.headers.get("Content-Length", "0") or "0")
        corpo = self.rfile.read(tamanho) if tamanho else None
        headers = {
            chave: valor
            for chave, valor in self.headers.items()
            if chave.lower()
            not in {"host", "connection", "content-length", "transfer-encoding", "accept-encoding"}
        }
        headers["Host"] = f"127.0.0.1:{API_PORT}"
        headers["Accept-Encoding"] = "identity"
        requisicao = urllib.request.Request(
            f"{API_URL}{self.path}",
            data=corpo,
            headers=headers,
            method=metodo,
        )
        try:
            with urllib.request.urlopen(requisicao, timeout=30) as resposta:
                dados = resposta.read()
                self.send_response(resposta.status)
                for chave, valor in resposta.headers.items():
                    if chave.lower() in {"content-length", "transfer-encoding", "connection"}:
                        continue
                    self.send_header(chave, valor)
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                if metodo != "HEAD":
                    self.wfile.write(dados)
        except urllib.error.HTTPError as erro:
            dados = erro.read()
            self.send_response(erro.code)
            for chave, valor in erro.headers.items():
                if chave.lower() in {"content-length", "transfer-encoding", "connection"}:
                    continue
                self.send_header(chave, valor)
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            if metodo != "HEAD":
                self.wfile.write(dados)
        except (urllib.error.URLError, OSError) as erro:
            dados = json.dumps({"detail": f"API de QA indisponível: {erro}"}).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            if metodo != "HEAD":
                self.wfile.write(dados)

    def _despachar(self, metodo: str) -> None:
        if self.path.startswith("/__ui_health"):
            dados = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            if metodo != "HEAD":
                self.wfile.write(dados)
            return
        if API_PREFIX.match(urllib.parse.urlparse(self.path).path):
            self._proxy(metodo)
            return
        if metodo in {"GET", "HEAD"}:
            self._servir_estatico(metodo)
            return
        self.send_error(405, "Método não permitido")

    def _despachar_seguro(self, metodo: str) -> None:
        # Chrome fecha conexões ociosas/concorrentes sem aviso; isso não é
        # falha da aplicação, só não deve virar traceback no servidor de QA.
        try:
            self._despachar(metodo)
        except (BrokenPipeError, ConnectionResetError):
            return

    def do_GET(self) -> None:  # noqa: N802
        self._despachar_seguro("GET")

    def do_HEAD(self) -> None:  # noqa: N802
        self._despachar_seguro("HEAD")

    def do_POST(self) -> None:  # noqa: N802
        self._despachar_seguro("POST")

    def do_PATCH(self) -> None:  # noqa: N802
        self._despachar_seguro("PATCH")

    def do_PUT(self) -> None:  # noqa: N802
        self._despachar_seguro("PUT")

    def do_DELETE(self) -> None:  # noqa: N802
        self._despachar_seguro("DELETE")

    def do_OPTIONS(self) -> None:  # noqa: N802
        try:
            self.send_response(200)
            self.send_header("Allow", "GET, HEAD, POST, PATCH, PUT, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, HEAD, POST, PATCH, PUT, DELETE, OPTIONS")
            self.send_header("Content-Length", "0")
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError):
            return


# --------------------------------------------------------------------------
# Infraestrutura de QA
# --------------------------------------------------------------------------
def esperar_http(url: str, timeout: float = 60.0) -> None:
    limite = time.monotonic() + timeout
    ultimo = ""
    while time.monotonic() < limite:
        try:
            with urllib.request.urlopen(url, timeout=2) as resposta:
                if resposta.status == 200:
                    return
                ultimo = f"HTTP {resposta.status}"
        except Exception as erro:  # noqa: BLE001 - polling de startup
            ultimo = str(erro)
        time.sleep(0.25)
    raise RuntimeError(f"Servidor não ficou pronto: {url} ({ultimo})")


def resetar_rate_limiter() -> None:
    requisicao = urllib.request.Request(
        f"{API_URL}/__ui_test/reset-rate-limit",
        method="POST",
        headers={"X-UI-Test-Token": RESET_TOKEN},
    )
    with urllib.request.urlopen(requisicao, timeout=5) as resposta:
        if resposta.status != 200:
            raise RuntimeError(f"reset do limiter devolveu {resposta.status}")


def preparar_banco() -> None:
    for sufixo in ("", "-wal", "-shm"):
        candidato = Path(f"{DB_PATH}{sufixo}")
        if candidato.exists():
            candidato.unlink()
    resultado = subprocess.run(
        [PYTHON, str(ROOT / "scripts" / "prepare_ui_backend.py")],
        cwd=ROOT,
        env=BACKEND_ENV,
        capture_output=True,
        text=True,
        check=False,
    )
    if resultado.returncode != 0:
        raise RuntimeError(
            f"prepare_ui_backend.py falhou ({resultado.returncode}):\n"
            f"{resultado.stdout}\n{resultado.stderr}"
        )


def iniciar_backend() -> subprocess.Popen:
    return subprocess.Popen(
        [PYTHON, str(ROOT / "scripts" / "ui_backend_server.py")],
        cwd=ROOT,
        env=BACKEND_ENV,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def iniciar_web() -> tuple[ThreadingHTTPServer, threading.Thread]:
    servidor = ThreadingHTTPServer(("0.0.0.0", WEB_PORT), WebHandler)
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    return servidor, thread


def assert_sem_overflow(page) -> None:
    medidas = page.evaluate(
        """() => ({
            conteudo: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth),
            viewport: window.innerWidth,
        })"""
    )
    assert medidas["conteudo"] <= medidas["viewport"] + 1, (
        f"documento com {medidas['conteudo']}px em viewport de {medidas['viewport']}px"
    )


def assert_api_same_origin(api_urls: list[str]) -> None:
    assert api_urls, "nenhuma chamada /api/ observada"
    for url in api_urls:
        assert urllib.parse.urlparse(url).netloc == f"127.0.0.1:{WEB_PORT}", url


def anexar_observadores(page, erros: list[str], api_urls: list[str]) -> None:
    def ao_responder(resposta) -> None:
        if resposta.status >= 500:
            erros.append(f"HTTP {resposta.status}: {resposta.url}")
        if "/api/" in resposta.url:
            api_urls.append(resposta.url)

    page.on("pageerror", lambda erro: erros.append(f"JS: {erro}"))
    page.on("response", ao_responder)
    page.on(
        "requestfailed",
        lambda requisicao: erros.append(f"REQ {requisicao.url}: {requisicao.failure}"),
    )


def esperar_login_hidratado(page, largura: int = 1440) -> None:
    """O pré-render do Expo Router é substituído na hidratação.

    Sem esta espera, um fill() pode cair no input do SSR e ser descartado —
    o mesmo cuidado do helpers.ts da suíte Node.
    """
    if largura < 1024:
        expect(page.get_by_text("Bem-vindo ao Smart Parking")).to_be_visible()
    else:
        expect(page.get_by_text("Acesse sua conta para continuar")).to_be_visible()


# --------------------------------------------------------------------------
# Jornadas Web
# --------------------------------------------------------------------------
def home_e_mapa(page, api_urls: list[str]) -> None:
    page.goto(BASE_URL + "/")
    expect(page.get_by_text(re.compile("Encontre Vagas de")).first).to_be_visible()
    cta = page.get_by_role("button", name=re.compile("Ver Vagas Disponíveis"))
    expect(cta).to_be_visible()
    assert cta.evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(37, 99, 235)"
    caixa = cta.bounding_box()
    assert caixa and caixa["height"] >= 44
    assert_sem_overflow(page)

    cta.click()
    expect(page).to_have_url(re.compile(r"/shopping/[^/]+$"))
    vaga = page.get_by_role("button", name=re.compile("Vaga A-01 — livre"))
    expect(vaga).to_be_visible()
    expect(page.get_by_role("button", name=re.compile("Vaga A-03 — ocupada"))).to_be_visible()
    caixa_vaga = vaga.bounding_box()
    assert caixa_vaga and caixa_vaga["width"] >= 44
    assert caixa_vaga and caixa_vaga["height"] >= 44
    assert_sem_overflow(page)
    assert_api_same_origin(api_urls)


def dropdown_hero(page, _api_urls: list[str]) -> None:
    page.goto(BASE_URL + "/")
    seletor = page.get_by_role("button", name=re.compile("Selecionar shopping:"))
    expect(seletor).to_be_visible()
    assert seletor.get_attribute("aria-expanded") == "false"
    seletor.click()
    assert seletor.get_attribute("aria-expanded") == "true"

    lista = page.get_by_role("list", name="Lista de shoppings")
    expect(lista).to_be_visible()
    assert lista.evaluate("el => getComputedStyle(el).position") == "absolute"
    caixa_seletor = seletor.bounding_box()
    caixa_lista = lista.bounding_box()
    assert caixa_seletor and caixa_lista
    assert caixa_lista["y"] >= caixa_seletor["y"] + caixa_seletor["height"] - 2
    expect(page.get_by_role("button", name=re.compile("Shopping QA Norte")).first).to_be_visible()

    page.keyboard.press("Escape")
    expect(lista).to_have_count(0)
    assert seletor.get_attribute("aria-expanded") == "false"
    assert_sem_overflow(page)


def explorar(page, _api_urls: list[str]) -> None:
    page.goto(BASE_URL + "/explorar")
    busca = page.get_by_placeholder("Buscar por shopping ou bairro…")
    expect(busca).to_be_visible()
    busca.fill("Norte")
    expect(page.get_by_text("Shopping QA Norte")).to_be_visible()
    expect(page.get_by_text("Shopping QA Centro")).to_have_count(0)
    busca.fill("shopping que não existe")
    expect(page.get_by_text("Nenhum shopping encontrado")).to_be_visible()
    busca.fill("Norte")
    page.get_by_text("Shopping QA Norte").click()
    expect(page).to_have_url(re.compile(r"/shopping/[^/]+$"))
    expect(page.get_by_role("button", name=re.compile("Vaga C-01 — livre"))).to_be_visible()


def responsividade_login(page, _api_urls: list[str]) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(BASE_URL + "/login")
    expect(page.get_by_text("Bem-vindo ao Smart Parking")).to_be_visible()
    entrar = page.get_by_role("button", name="Entrar", exact=True)
    caixa = entrar.bounding_box()
    assert caixa and caixa["height"] >= 44
    assert_sem_overflow(page)
    page.get_by_role("button", name=re.compile("Voltar ao Início")).click()
    expect(page).to_have_url(re.compile(r"/$"))
    expect(page.get_by_text("Shopping QA Centro").first).to_be_visible()
    assert_sem_overflow(page)

    page.set_viewport_size({"width": 900, "height": 900})
    page.goto(BASE_URL + "/login")
    expect(page.get_by_text("Bem-vindo ao Smart Parking")).to_be_visible()
    # O split agora é CSS puro: o painel existe no DOM em 900px, mas está
    # escondido por `hidden lg:flex`. O que importa é não estar visível.
    expect(page.get_by_text("Monitoramento inteligente de vagas", exact=False)).to_be_hidden()
    assert_sem_overflow(page)

    page.set_viewport_size({"width": 1024, "height": 900})
    page.goto(BASE_URL + "/login")
    expect(page.get_by_text("Acesse sua conta para continuar")).to_be_visible()
    assert_sem_overflow(page)


def formulario_acessivel(page, _api_urls: list[str]) -> None:
    page.goto(BASE_URL + "/login")
    esperar_login_hidratado(page)
    page.get_by_role("button", name="Entrar", exact=True).click()
    email = page.get_by_label("E-mail ou telefone", exact=True)
    assert email.get_attribute("aria-invalid") == "true"
    assert email.get_attribute("aria-required") == "true"
    expect(page.get_by_text("Informe seu e-mail ou telefone")).to_be_visible()
    mostrar = page.get_by_role("button", name="Mostrar senha")
    expect(mostrar).to_be_visible()
    mostrar.click()
    expect(page.get_by_role("button", name="Ocultar senha")).to_be_visible()


def movimento_reduzido(page, _api_urls: list[str]) -> None:
    page.goto(BASE_URL + "/login")
    esperar_login_hidratado(page)
    entrar = page.get_by_role("button", name="Entrar", exact=True)
    expect(entrar).to_have_css("transition-property", "none")
    entrar.hover()
    expect(entrar).to_have_css("background-color", "rgb(29, 78, 216)")
    page.mouse.down()
    assert entrar.evaluate("el => getComputedStyle(el).transform") == "none"
    page.mouse.move(0, 0)
    page.mouse.up()


def painel_admin(page, _api_urls: list[str]) -> None:
    page.goto(BASE_URL + "/login")
    esperar_login_hidratado(page)
    page.get_by_label("E-mail ou telefone", exact=True).fill("admin@smartparking.com")
    page.get_by_label("Senha", exact=True).fill("admin123")
    page.get_by_role("button", name="Entrar", exact=True).click()
    expect(page).to_have_url(re.compile(r"/dashboard$"))
    expect(page.get_by_text("Visão geral em tempo real")).to_be_visible()
    page.get_by_text("Usuários", exact=True).click()
    expect(page.get_by_role("button", name=re.compile("Novo usuário"))).to_be_visible()
    page.get_by_text("Estacionamentos", exact=True).click()
    expect(page.get_by_role("button", name=re.compile("Novo estacionamento"))).to_be_visible()
    page.get_by_text("Relatórios", exact=True).click()
    expect(page.get_by_role("button", name="CSV financeiro")).to_be_visible()


def reserva_e_cancelamento(page, _api_urls: list[str]) -> None:
    page.on("dialog", lambda dialog: dialog.accept())
    page.goto(BASE_URL + "/login")
    esperar_login_hidratado(page)
    page.get_by_label("E-mail ou telefone", exact=True).fill("motorista@smartparking.com")
    page.get_by_label("Senha", exact=True).fill("motor123")
    page.get_by_role("button", name="Entrar", exact=True).click()
    expect(page.get_by_text("Minhas reservas").first).to_be_visible()

    page.goto(BASE_URL + "/")
    page.get_by_role("button", name=re.compile("Ver Vagas Disponíveis")).click()
    expect(page).to_have_url(re.compile(r"/shopping/[^/]+$"))
    page.get_by_role("button", name=re.compile("Vaga A-02 — livre")).click()
    page.get_by_role("button", name="Reservar por 2h", exact=True).click()
    expect(page.get_by_text("Confirmada", exact=True)).to_be_visible()
    page.get_by_role("button", name="Cancelar", exact=True).first.click()
    expect(page.get_by_text("Cancelada", exact=True)).to_be_visible()

    with urllib.request.urlopen(f"{BASE_URL}/api/estacionamentos", timeout=10) as resposta:
        estacionamentos = json.load(resposta)
    centro = next(e for e in estacionamentos if e["nome"] == "Shopping QA Centro")
    with urllib.request.urlopen(
        f"{BASE_URL}/api/estacionamentos/{centro['id']}/vagas", timeout=10
    ) as resposta:
        dados = json.load(resposta)
    vaga = next(v for v in dados["vagas"] if v["codigo"] == "A-02")
    assert vaga["status"] == "livre", f"API não refletiu cancelamento: {vaga['status']}"


def desempenho(page, _api_urls: list[str]) -> None:
    page.goto(BASE_URL + "/")
    expect(page.get_by_text("Shopping QA Centro").first).to_be_visible()
    fcp = page.evaluate(
        "performance.getEntriesByName('first-contentful-paint')[0]?.startTime || 0"
    )
    assert 0 < fcp < 4000, f"FCP fora do orçamento: {fcp}ms"

    urls = [
        f"{BASE_URL}/api/estacionamentos" if indice % 2 == 0 else f"{BASE_URL}/health"
        for indice in range(24)
    ]

    def buscar(url: str) -> float:
        inicio = time.perf_counter()
        with urllib.request.urlopen(url, timeout=5) as resposta:
            assert resposta.status == 200, f"{url} -> {resposta.status}"
            resposta.read()
        return time.perf_counter() - inicio

    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=8) as pool:
        duracoes = list(pool.map(buscar, urls))
    total = time.perf_counter() - inicio
    p95 = sorted(duracoes)[max(0, int(len(duracoes) * 0.95) - 1)]
    print(
        f"METRICAS_DESEMPENHO fcp={fcp:.0f}ms p95={p95 * 1000:.0f}ms "
        f"lote24={total * 1000:.0f}ms",
        flush=True,
    )
    assert p95 < 1.0, f"p95 acima de 1s: {p95:.3f}s"
    assert total < 5.0, f"lote de 24 acima de 5s: {total:.3f}s"


CENARIOS = [
    ("home, CTA e mapa público", home_e_mapa, None),
    ("dropdown flutuante e Escape", dropdown_hero, None),
    ("explorar com filtro e vazio", explorar, None),
    ("login responsivo 390/900/1024", responsividade_login, None),
    ("formulário com ARIA e senha", formulario_acessivel, None),
    ("prefers-reduced-motion", movimento_reduzido, "reduce"),
    ("painel admin e abas", painel_admin, None),
    ("reserva e cancelamento com API real", reserva_e_cancelamento, None),
    ("desempenho Web e API concorrente", desempenho, None),
]


def executar_cenario(browser, nome: str, funcao, reduced_motion) -> bool:
    resetar_rate_limiter()
    contexto = browser.new_context(
        base_url=BASE_URL,
        viewport={"width": 1440, "height": 900},
        reduced_motion=reduced_motion,
    )
    contexto.set_default_timeout(15_000)
    page = contexto.new_page()
    page.set_default_timeout(15_000)
    page.set_default_navigation_timeout(30_000)
    erros: list[str] = []
    api_urls: list[str] = []
    anexar_observadores(page, erros, api_urls)
    try:
        funcao(page, api_urls)
        assert not erros, "erros de runtime/5xx: " + " | ".join(erros)
        print(f"PASS {nome}", flush=True)
        return True
    except Exception as erro:  # noqa: BLE001 - relatório por cenário
        print(f"FAIL {nome}: {erro}", flush=True)
        return False
    finally:
        contexto.close()


def main() -> None:
    if not DIST.is_dir():
        raise SystemExit(
            f"Bundle Web ausente em {DIST}. Rode antes: "
            "expo export --platform web --output-dir src/frontend/smart-parking/dist"
        )

    executavel = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
    launch_kwargs: dict = {
        "headless": True,
        "args": ["--no-sandbox", "--disable-dev-shm-usage"],
    }
    if executavel:
        launch_kwargs["executable_path"] = executavel
        ambiente = dict(os.environ)
        if os.environ.get("PLAYWRIGHT_CHROMIUM_LD_LIBRARY_PATH"):
            ambiente["LD_LIBRARY_PATH"] = os.environ["PLAYWRIGHT_CHROMIUM_LD_LIBRARY_PATH"]
        if os.environ.get("PLAYWRIGHT_CHROMIUM_FONTCONFIG_PATH"):
            ambiente["FONTCONFIG_PATH"] = os.environ["PLAYWRIGHT_CHROMIUM_FONTCONFIG_PATH"]
        ambiente.setdefault("HOME", "/tmp")
        launch_kwargs["env"] = ambiente

    backend = None
    servidor = None
    thread = None
    try:
        preparar_banco()
        backend = iniciar_backend()
        esperar_http(f"{API_URL}/health", 60)
        servidor, thread = iniciar_web()
        esperar_http(f"{BASE_URL}/__ui_health", 30)

        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_kwargs)
            try:
                falhas = [
                    nome
                    for nome, funcao, reduzido in CENARIOS
                    if not executar_cenario(browser, nome, funcao, reduzido)
                ]
                total = len(CENARIOS)
                print(f"\n{total - len(falhas)}/{total} cenários aprovados", flush=True)
                if falhas:
                    raise SystemExit(1)
            finally:
                browser.close()
    finally:
        if servidor is not None:
            servidor.shutdown()
            servidor.server_close()
        if thread is not None:
            thread.join(timeout=5)
        if backend is not None and backend.poll() is None:
            try:
                backend.terminate()
                backend.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend.kill()
                backend.wait(timeout=5)


if __name__ == "__main__":
    main()
