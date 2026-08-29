from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from models import Dispositivo
from services.energia import resumo_consumo, tarifa_atual, custo
from services.relatorios import gerar_relatorio

bp = Blueprint("energia", __name__, url_prefix="/energia")


def _periodo_semana():
    fim = datetime.now(timezone.utc)
    inicio = fim - timedelta(days=7)
    return inicio, fim


@bp.route("/")
@login_required
def painel():
    inicio, fim = _periodo_semana()
    dispositivos = Dispositivo.query.all()
    linhas = resumo_consumo(dispositivos, inicio, fim)
    kwh_total = sum(kwh for _, kwh in linhas)
    tarifa = tarifa_atual()
    custo_total = custo(kwh_total, tarifa)

    # consumo agrupado por cômodo, para o gráfico
    por_comodo = {}
    for dispositivo, kwh in linhas:
        nome_comodo = dispositivo.comodo.nome
        por_comodo[nome_comodo] = por_comodo.get(nome_comodo, 0.0) + kwh

    return render_template(
        "energia.html",
        linhas=linhas[:8],
        por_comodo=sorted(por_comodo.items(), key=lambda x: x[1], reverse=True),
        kwh_total=kwh_total,
        custo_total=custo_total,
        tarifa=tarifa,
        inicio=inicio,
        fim=fim,
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
