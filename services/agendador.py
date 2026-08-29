"""
Agendador de automações — faz as rotinas salvas em `Automacao` dispararem
sozinhas, no horário configurado, chamando `dispositivo.ligar()`/`desligar()`
de verdade (o que também gera o `RegistroUso` correspondente, com
`usuario=None` marcando que foi a automação e não uma pessoa).

Roda em background dentro do próprio processo do Flask (APScheduler), sem
precisar de um serviço externo — checa a cada minuto se alguma automação
ativa bate com o horário e o dia da semana atuais (fuso `config.TIMEZONE`).
"""
import atexit
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from extensions import db
from models import Automacao

# 'todos' = dispara todo dia; senão, lista separada por vírgula com estas siglas.
_DIAS_ABREV = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]


def _dia_bate(dias_semana, hoje_weekday):
    dias_semana = (dias_semana or "todos").strip().lower()
    if dias_semana == "todos":
        return True
    dias_pedidos = {d.strip() for d in dias_semana.split(",") if d.strip()}
    return _DIAS_ABREV[hoje_weekday] in dias_pedidos


def _executar_automacoes_pendentes(app):
    with app.app_context():
        agora_local = datetime.now(ZoneInfo(app.config["TIMEZONE"]))
        horario_atual = agora_local.strftime("%H:%M")

        automacoes = Automacao.query.filter_by(ativa=True, horario=horario_atual).all()
        for automacao in automacoes:
            if not _dia_bate(automacao.dias_semana, agora_local.weekday()):
                continue
            for acao in automacao.acoes:
                dispositivo = acao.dispositivo
                if dispositivo is None:
                    continue
                if acao.acao == "ligar":
                    dispositivo.ligar(usuario=None)
                elif acao.acao == "desligar":
                    dispositivo.desligar(usuario=None)

        if automacoes:
            db.session.commit()


def proxima_automacao(tz):
    """Automação ativa que vai disparar mais cedo a partir de agora (dentro
    dos próximos 7 dias), junto com o horário exato em que isso acontece.
    Usada pra mostrar o banner "Próxima automação" no painel.

    Retorna (Automacao, datetime) ou (None, None) se não houver nenhuma."""
    agora_local = datetime.now(tz)

    melhor, melhor_quando = None, None
    for automacao in Automacao.query.filter_by(ativa=True).all():
        partes = (automacao.horario or "").split(":")
        if len(partes) != 2:
            continue
        try:
            hora, minuto = int(partes[0]), int(partes[1])
        except ValueError:
            continue

        for dias_a_frente in range(8):
            candidato_dia = agora_local + timedelta(days=dias_a_frente)
            if not _dia_bate(automacao.dias_semana, candidato_dia.weekday()):
                continue
            quando = candidato_dia.replace(hour=hora, minute=minuto, second=0, microsecond=0)
            if quando <= agora_local:
                continue
            if melhor_quando is None or quando < melhor_quando:
                melhor, melhor_quando = automacao, quando
            break

    return melhor, melhor_quando


def rotulo_quando(quando, tz):
    """'Hoje às 19:00' / 'Amanhã às 07:00' / 'Segunda às 18:30'."""
    agora_local = datetime.now(tz)
    if quando.date() == agora_local.date():
        return f"Hoje às {quando.strftime('%H:%M')}"
    if quando.date() == (agora_local + timedelta(days=1)).date():
        return f"Amanhã às {quando.strftime('%H:%M')}"
    dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    return f"{dias[quando.weekday()]} às {quando.strftime('%H:%M')}"


def iniciar_agendador(app):
    """Registra e liga o BackgroundScheduler no app Flask fornecido.

    Sob o reloader do Flask (debug=True) o processo sobe duplicado; só
    inicia de fato no processo filho que realmente serve as requisições,
    senão a automação disparava duas vezes por minuto.
    """
    import os
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return None

    scheduler = BackgroundScheduler(timezone=ZoneInfo(app.config["TIMEZONE"]))
    scheduler.add_job(
        _executar_automacoes_pendentes,
        args=[app],
        trigger=CronTrigger(second=0),
        id="automacoes",
        replace_existing=True,
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))
    return scheduler
