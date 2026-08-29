"""
Cálculo de consumo de energia a partir do histórico de uso (RegistroUso).

A ideia: cada Dispositivo tem uma potência em Watts. Emparelhando eventos
consecutivos "ligou" -> "desligou" no RegistroUso, sabemos por quanto tempo
o dispositivo ficou ligado num período. tempo_ligado (h) × potência (W) / 1000
= kWh consumidos. Multiplicando pela tarifa vigente, chegamos ao custo em R$.

Isso é calculado sob demanda (não fica pré-armazenado em outra tabela) —
para o volume de dados de uma casa simulada isso é rápido o suficiente, e
evita ter uma tabela derivada para manter sincronizada.
"""
from datetime import datetime, timedelta, timezone

from models import RegistroUso, TarifaEnergia, Dispositivo


def tarifa_atual():
    """Retorna a TarifaEnergia vigente (a mais recente sem vigente_ate)."""
    return (
        TarifaEnergia.query.filter(TarifaEnergia.vigente_ate.is_(None))
        .order_by(TarifaEnergia.vigente_desde.desc())
        .first()
    )


def kwh_consumidos(dispositivo: Dispositivo, inicio: datetime, fim: datetime) -> float:
    """kWh consumidos por um dispositivo entre `inicio` e `fim`."""
    eventos = (
        RegistroUso.query.filter(
            RegistroUso.dispositivo_id == dispositivo.id,
            RegistroUso.timestamp <= fim,
        )
        .order_by(RegistroUso.timestamp)
        .all()
    )

    horas_ligado = 0.0
    ligou_em = None
    for ev in eventos:
        ts = ev.timestamp if ev.timestamp.tzinfo else ev.timestamp.replace(tzinfo=timezone.utc)
        if ev.evento == "ligou":
            ligou_em = max(ts, inicio)
        elif ev.evento == "desligou" and ligou_em is not None:
            fim_intervalo = min(ts, fim)
            if fim_intervalo > ligou_em:
                horas_ligado += (fim_intervalo - ligou_em).total_seconds() / 3600
            ligou_em = None

    # se ainda está ligado no fim do período (não desligou), conta até `fim`
    if ligou_em is not None and dispositivo.ativo:
        if fim > ligou_em:
            horas_ligado += (fim - ligou_em).total_seconds() / 3600

    return horas_ligado * dispositivo.potencia_watts / 1000


def resumo_consumo(dispositivos, inicio: datetime, fim: datetime):
    """Para uma lista de dispositivos, devolve [(dispositivo, kwh), ...]
    ordenado do que mais consome para o que menos consome."""
    linhas = [(d, kwh_consumidos(d, inicio, fim)) for d in dispositivos]
    linhas.sort(key=lambda par: par[1], reverse=True)
    return linhas


def custo(kwh: float, tarifa: TarifaEnergia | None) -> float:
    if not tarifa:
        return 0.0
    return kwh * tarifa.valor_kwh


def variacao_percentual(atual: float, anterior: float) -> float | None:
    """% de mudança de `anterior` para `atual`. None quando não há base de
    comparação (período anterior sem consumo nenhum) — não dá pra calcular
    variação percentual em cima de zero."""
    if not anterior:
        return None
    return (atual - anterior) / anterior * 100


def projecao_mensal(kwh_periodo: float, dias_periodo: int) -> float:
    """Projeta o consumo do período pro mês (30 dias), mantendo o ritmo atual."""
    if dias_periodo <= 0:
        return 0.0
    return kwh_periodo / dias_periodo * 30


def gerar_alerta(dispositivos, inicio: datetime, fim: datetime, limiar_pct: float = 15.0, kwh_minimo: float = 0.3):
    """Insight simples baseado em regra: compara o consumo de cada dispositivo
    nesta semana com a semana anterior e aponta o que mais cresceu, se o
    crescimento for relevante (acima de `limiar_pct`) e não for ruído
    (consumo mínimo de `kwh_minimo` kWh, pra não disparar em dispositivo que
    mal liga).

    Retorna um dict {dispositivo, kwh_atual, variacao} ou None se nada relevante."""
    duracao = fim - inicio
    inicio_anterior = inicio - duracao

    melhor = None
    for dispositivo in dispositivos:
        atual = kwh_consumidos(dispositivo, inicio, fim)
        if atual < kwh_minimo:
            continue
        anterior = kwh_consumidos(dispositivo, inicio_anterior, inicio)
        if anterior < kwh_minimo:
            # sem base de comparação minimamente confiável — não dá pra dizer
            # que "cresceu X%" em cima de um período que mal teve uso.
            continue
        variacao = variacao_percentual(atual, anterior)
        if variacao is None or variacao < limiar_pct:
            continue
        if melhor is None or variacao > melhor["variacao"]:
            melhor = {"dispositivo": dispositivo, "kwh_atual": atual, "variacao": variacao}

    return melhor


_DIAS_ABREV = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def consumo_diario_por_comodo(dispositivos, comodos_ordenados, dias: int = 7, fim: datetime | None = None):
    """kWh consumidos por dia (últimos `dias` dias completos, mais antigo
    primeiro) quebrado por cômodo — matéria-prima do gráfico empilhado do
    painel de energia. `comodos_ordenados` fixa a ordem/cor de cada cômodo
    (a mesma em todo dia, pra cor nunca trocar de sentido no gráfico)."""
    fim = fim or datetime.now(timezone.utc)
    fim_hoje = fim.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

    dias_resultado = []
    for i in range(dias - 1, -1, -1):
        inicio_dia = min(fim_hoje - timedelta(days=i + 1), fim)
        fim_dia = min(fim_hoje - timedelta(days=i), fim)

        por_comodo = {c.nome: 0.0 for c in comodos_ordenados}
        for dispositivo in dispositivos:
            kwh = kwh_consumidos(dispositivo, inicio_dia, fim_dia)
            if kwh > 0:
                por_comodo[dispositivo.comodo.nome] = por_comodo.get(dispositivo.comodo.nome, 0.0) + kwh

        dias_resultado.append({
            "label": _DIAS_ABREV[inicio_dia.weekday()],
            "segmentos": list(por_comodo.items()),
            "total": sum(por_comodo.values()),
        })

    return dias_resultado
