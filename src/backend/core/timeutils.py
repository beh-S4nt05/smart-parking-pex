"""
Utilidades de tempo do SmartParking (ADR-05 · RNF-09 · ACH-01).

Regra única para todo o backend:
- Escreva timestamps como **UTC naive** (`utc_agora()`): o SQLite armazena
  a parede UTC sem offset e o Postgres (coluna timestamptz, sessão UTC do
  container) interpreta o mesmo instante — os dois bancos ficam coerentes.
- Compare janelas de relatório em **naive-UTC derivado do dia de Manaus**:
  "hoje" = a meia-noite em America/Manaus convertida para UTC (UTC-3 fixo;
  o Amazonas não tem horário de verão, então não dependemos de tzdata).
- Valores vindos do banco passam por `normalizar()` antes de comparação em
  Python (SQLite devolve naive, Postgres devolve aware — `normalizar` unifica).
"""

from datetime import datetime, timedelta, timezone

# America/Manaus: UTC-3 permanente (sem DST) — evita dependência de tzdata
FUSO_MANAUS = timezone(timedelta(hours=-3))


def utc_agora() -> datetime:
    """Agora em UTC, naive — formato canônico de GRAVAÇÃO no banco."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalizar(dt: datetime) -> datetime:
    """Qualquer datetime vindo do banco → naive-UTC (comparável com utc_agora())."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.replace(tzinfo=None)


def inicio_dia_manaus(ref: datetime | None = None) -> datetime:
    """Meia-noite do "dia de hoje" (calendário de Manaus) em naive-UTC."""
    base = ref or datetime.now(timezone.utc)
    local = base.astimezone(FUSO_MANAUS)
    return normalizar(local.replace(hour=0, minute=0, second=0, microsecond=0))


def janela_manaus(periodo: str) -> tuple[datetime, datetime]:
    """
    [início, fim) do período SEMPRE ancorado no dia local de Manaus
    (RN-12). `periodo` ∈ {diario, semanal, mensal}.
    Levanta ValueError para período inválido (a camada de rota converte em 400).
    """
    hoje = inicio_dia_manaus()
    if periodo == "diario":
        return hoje, hoje + timedelta(days=1)
    if periodo == "semanal":
        inicio_semana = hoje - timedelta(days=hoje.weekday())  # segunda-feira
        return inicio_semana, inicio_semana + timedelta(days=7)
    if periodo == "mensal":
        inicio_mes = hoje.replace(day=1)
        if inicio_mes.month == 12:
            fim_mes = inicio_mes.replace(year=inicio_mes.year + 1, month=1)
        else:
            fim_mes = inicio_mes.replace(month=inicio_mes.month + 1)
        return inicio_mes, fim_mes
    raise ValueError("Período inválido. Use: diario, semanal ou mensal")


def janela_dias_manaus(dias: int) -> tuple[datetime, datetime]:
    """Últimos `dias` dias de calendário (Manaus), terminando no fim de hoje."""
    hoje = inicio_dia_manaus()
    dias = max(1, min(int(dias), 90))
    return hoje - timedelta(days=dias - 1), hoje + timedelta(days=1)
