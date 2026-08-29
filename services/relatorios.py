"""
Geração (e, se configurado, envio) do relatório semanal de consumo por e-mail.

Sem SMTP_HOST/SMTP_USER/SMTP_SENHA configurados (ver config.py), a função só
gera o relatório, salva um RelatorioEnviado (com enviado_de_verdade=False) e
devolve o HTML para pré-visualização na tela — assim a funcionalidade é
código real e demonstrável mesmo sem credenciais de e-mail configuradas.
Com as variáveis de ambiente configuradas, ela também dispara o e-mail via
smtplib de verdade.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app, render_template

from extensions import db
from models import Dispositivo, RelatorioEnviado
from services.energia import resumo_consumo, tarifa_atual, custo


def gerar_relatorio(usuario, inicio, fim):
    dispositivos = Dispositivo.query.all()
    linhas = resumo_consumo(dispositivos, inicio, fim)
    kwh_total = sum(kwh for _, kwh in linhas)
    tarifa = tarifa_atual()
    custo_total = custo(kwh_total, tarifa)

    relatorio = RelatorioEnviado(
        usuario_id=usuario.id,
        periodo_inicio=inicio,
        periodo_fim=fim,
        kwh_total=kwh_total,
        custo_total=custo_total,
        tarifa_usada=tarifa.valor_kwh if tarifa else 0.0,
    )

    html = render_template(
        "email_relatorio.html",
        usuario=usuario,
        linhas=linhas[:5],
        kwh_total=kwh_total,
        custo_total=custo_total,
        inicio=inicio,
        fim=fim,
    )

    enviado = _tentar_enviar_email(usuario, html)
    relatorio.enviado_de_verdade = enviado

    db.session.add(relatorio)
    db.session.commit()
    return relatorio, html


def _tentar_enviar_email(usuario, html):
    cfg = current_app.config
    if not (cfg.get("SMTP_HOST") and cfg.get("SMTP_USER") and cfg.get("SMTP_SENHA")):
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Seu resumo semanal de energia — PULSE2050"
    msg["From"] = cfg["SMTP_REMETENTE"]
    msg["To"] = usuario.email
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"]) as servidor:
            servidor.starttls()
            servidor.login(cfg["SMTP_USER"], cfg["SMTP_SENHA"])
            servidor.sendmail(cfg["SMTP_REMETENTE"], [usuario.email], msg.as_string())
        return True
    except Exception:
        current_app.logger.exception("Falha ao enviar relatório por e-mail")
        return False
