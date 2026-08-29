from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user

from extensions import db
from models import Comodo, Dispositivo, Luz, Automacao, AutomacaoAcao, RegistroUso

bp = Blueprint("main", __name__)


@bp.route("/")
@login_required
def dashboard():
    comodos = Comodo.query.order_by(Comodo.id).all()
    total_dispositivos = Dispositivo.query.count()
    ativos = Dispositivo.query.filter_by(ativo=True).count()
    return render_template(
        "dashboard.html", comodos=comodos, total_dispositivos=total_dispositivos, ativos=ativos
    )


def _get_dispositivo_ou_404(dispositivo_id):
    dispositivo = db.session.get(Dispositivo, dispositivo_id)
    if dispositivo is None:
        abort(404)
    return dispositivo


@bp.route("/dispositivo/<int:dispositivo_id>")
@login_required
def detalhe_dispositivo(dispositivo_id):
    dispositivo = _get_dispositivo_ou_404(dispositivo_id)

    inicio_hoje = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    registros_hoje = (
        RegistroUso.query.filter(
            RegistroUso.dispositivo_id == dispositivo.id,
            RegistroUso.timestamp >= inicio_hoje,
        )
        .order_by(RegistroUso.timestamp)
        .all()
    )

    return render_template(
        "device_detail.html",
        dispositivo=dispositivo,
        registros_hoje=registros_hoje,
        automacoes=Automacao.query.join(AutomacaoAcao).filter(AutomacaoAcao.dispositivo_id == dispositivo.id).all(),
    )


@bp.route("/dispositivo/<int:dispositivo_id>/alternar", methods=["POST"])
@login_required
def alternar_dispositivo(dispositivo_id):
    dispositivo = _get_dispositivo_ou_404(dispositivo_id)

    if not dispositivo.pode_controlar(current_user):
        flash(f"Seu perfil não tem permissão para controlar {dispositivo.nome}.", "erro")
        return redirect(request.referrer or url_for("main.dashboard"))

    dispositivo.alternar(current_user)
    db.session.commit()
    return redirect(request.referrer or url_for("main.dashboard"))


@bp.route("/dispositivo/<int:dispositivo_id>/intensidade", methods=["POST"])
@login_required
def ajustar_intensidade(dispositivo_id):
    dispositivo = _get_dispositivo_ou_404(dispositivo_id)

    if not isinstance(dispositivo, Luz):
        abort(400)
    if not dispositivo.pode_controlar(current_user):
        flash("Seu perfil não tem permissão para controlar este dispositivo.", "erro")
        return redirect(url_for("main.detalhe_dispositivo", dispositivo_id=dispositivo.id))

    # --- Validação de dados: o campo tem que ser um número inteiro 1-100 ---
    bruto = (request.form.get("intensidade") or "").strip()
    if not bruto.isdigit():
        flash("Intensidade precisa ser um número entre 1 e 100.", "erro")
        return redirect(url_for("main.detalhe_dispositivo", dispositivo_id=dispositivo.id))

    dispositivo.ajustar_intensidade(int(bruto), current_user)
    db.session.commit()
    flash("Intensidade atualizada.", "sucesso")
    return redirect(url_for("main.detalhe_dispositivo", dispositivo_id=dispositivo.id))


@bp.route("/dispositivo/<int:dispositivo_id>/permissao", methods=["POST"])
@login_required
def alternar_permissao(dispositivo_id):
    if not current_user.is_admin:
        abort(403)
    dispositivo = _get_dispositivo_ou_404(dispositivo_id)
    dispositivo.controlavel_por_comum = not dispositivo.controlavel_por_comum
    db.session.commit()
    return redirect(url_for("main.detalhe_dispositivo", dispositivo_id=dispositivo.id))


@bp.route("/dispositivo/<int:dispositivo_id>/automacao", methods=["POST"])
@login_required
def criar_automacao(dispositivo_id):
    dispositivo = _get_dispositivo_ou_404(dispositivo_id)

    nome = (request.form.get("nome") or "").strip()
    horario = (request.form.get("horario") or "").strip()
    acao = request.form.get("acao")

    # --- Validação de dados ---
    def _horario_valido(h):
        if len(h) != 5 or h[2] != ":" or not h.replace(":", "").isdigit():
            return False
        hora, minuto = h.split(":")
        return 0 <= int(hora) <= 23 and 0 <= int(minuto) <= 59

    valido_horario = _horario_valido(horario)
    if not nome or not valido_horario or acao not in ("ligar", "desligar"):
        flash("Preencha nome, um horário válido (HH:MM) e a ação.", "erro")
        return redirect(url_for("main.detalhe_dispositivo", dispositivo_id=dispositivo.id))

    automacao = Automacao(nome=nome, horario=horario, criado_por=current_user)
    automacao.acoes.append(AutomacaoAcao(dispositivo=dispositivo, acao=acao))
    db.session.add(automacao)
    db.session.commit()
    flash("Automação criada.", "sucesso")
    return redirect(url_for("main.detalhe_dispositivo", dispositivo_id=dispositivo.id))
