from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from models import Comodo, Dispositivo
from services.energia import (
    resumo_consumo, tarifa_atual, custo, variacao_percentual, projecao_mensal,
    gerar_alerta, consumo_diario_por_comodo,
)
from services.relatorios import gerar_relatorio

bp = Blueprint("energia", __name__, url_prefix="/energia")

# cor fixa por cômodo (slots 1-5 da paleta categórica, ordem = Comodo.id) —
# a mesma cor em todo gráfico da página, nunca escolhida pela posição do dia.
_CORES_SERIE = ["serie-1", "serie-2", "serie-3", "serie-4", "serie-5", "serie-6", "serie-7", "serie-8"]


def _periodo_semana():
    fim = datetime.now(timezone.utc)
    inicio = fim - timedelta(days=7)
    return inicio, fim


@bp.route("/")
@login_required
def painel():
    inicio, fim = _periodo_semana()
    inicio_anterior = inicio - (fim - inicio)

    dispositivos = Dispositivo.query.all()
    comodos = Comodo.query.order_by(Comodo.id).all()
    cor_comodo = {c.nome: _CORES_SERIE[i % len(_CORES_SERIE)] for i, c in enumerate(comodos)}

    linhas = resumo_consumo(dispositivos, inicio, fim)
    kwh_total = sum(kwh for _, kwh in linhas)
    tarifa = tarifa_atual()
    custo_total = custo(kwh_total, tarifa)

    kwh_total_anterior = sum(kwh for _, kwh in resumo_consumo(dispositivos, inicio_anterior, inicio))
    variacao_semana = variacao_percentual(kwh_total, kwh_total_anterior)
    projecao_kwh = projecao_mensal(kwh_total, dias_periodo=7)
    projecao_custo = custo(projecao_kwh, tarifa)

    alerta = gerar_alerta(dispositivos, inicio, fim)

    # consumo agrupado por cômodo, para a lista "Consumo por cômodo"
    por_comodo = {}
    for dispositivo, kwh in linhas:
        nome_comodo = dispositivo.comodo.nome
        por_comodo[nome_comodo] = por_comodo.get(nome_comodo, 0.0) + kwh

    diario = consumo_diario_por_comodo(dispositivos, comodos, dias=7, fim=fim)
    teto_diario = max((dia["total"] for dia in diario), default=0.0)

    return render_template(
        "energia.html",
        linhas=linhas[:8],
        por_comodo=sorted(por_comodo.items(), key=lambda x: x[1], reverse=True),
        cor_comodo=cor_comodo,
        comodos=comodos,
        kwh_total=kwh_total,
        custo_total=custo_total,
        variacao_semana=variacao_semana,
        projecao_kwh=projecao_kwh,
        projecao_custo=projecao_custo,
        alerta=alerta,
        tarifa=tarifa,
        inicio=inicio,
        fim=fim,
        diario=diario,
        teto_diario=teto_diario,
    )


@bp.route("/relatorio", methods=["GET", "POST"])
@login_required
def relatorio():
    inicio, fim = _periodo_semana()

    if request.method == "POST":
        relatorio_obj, html = gerar_relatorio(current_user, inicio, fim)
        return render_template(
            "email_relatorio_pagina.html", relatorio=relatorio_obj, html_email=html
        )

    return render_template("relatorio_confirmar.html", inicio=inicio, fim=fim)
