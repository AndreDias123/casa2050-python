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
    """Painel de energia: consumo/custo da semana, comparação com a semana
    anterior, alerta de dispositivo que mais cresceu, e o gráfico diário por
    cômodo. Tudo calculado na hora a partir do RegistroUso — nada fica
    pré-armazenado, então não existe risco de o painel mostrar número velho."""
    inicio, fim = _periodo_semana()
    inicio_anterior = inicio - (fim - inicio)  # mesma duração, período anterior — base de comparação

    dispositivos = Dispositivo.query.all()
    comodos = Comodo.query.order_by(Comodo.id).all()
    # Cor fixa por cômodo, calculada uma vez aqui e reaproveitada em todo
    # gráfico da página (ver _CORES_SERIE acima).
    cor_comodo = {c.nome: _CORES_SERIE[i % len(_CORES_SERIE)] for i, c in enumerate(comodos)}

    # --- consumo da semana atual ---
    linhas = resumo_consumo(dispositivos, inicio, fim)
    kwh_total = sum(kwh for _, kwh in linhas)
    tarifa = tarifa_atual()
    custo_total = custo(kwh_total, tarifa)

    # --- comparação com a semana anterior + projeção do mês ---
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

    # --- matéria-prima do gráfico empilhado (um valor por dia/cômodo) ---
    diario = consumo_diario_por_comodo(dispositivos, comodos, dias=7, fim=fim)
    teto_diario = max((dia["total"] for dia in diario), default=0.0)  # maior dia = topo do eixo Y

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
    """GET mostra uma tela de confirmação; POST de fato gera o relatório
    (services/relatorios.py) e mostra o resultado — separado em duas etapas
    pra não gerar (e tentar mandar e-mail) só de alguém visitar a página."""
    inicio, fim = _periodo_semana()

    if request.method == "POST":
        relatorio_obj, html = gerar_relatorio(current_user, inicio, fim)
        return render_template(
            "email_relatorio_pagina.html", relatorio=relatorio_obj, html_email=html
        )

    return render_template("relatorio_confirmar.html", inicio=inicio, fim=fim)
