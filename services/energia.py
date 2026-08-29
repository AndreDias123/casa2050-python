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
from datetime import datetime, timezone

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
