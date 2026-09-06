import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Configuração da aplicação, lida de variável de ambiente quando existe,
    com um valor padrão que funciona pra rodar local sem configurar nada."""

    # Em produção, defina SECRET_KEY como variável de ambiente. É essa chave
    # que assina o cookie de sessão (login) e os tokens de CSRF — se ela
    # vazasse ou fosse previsível, dava pra forjar sessão de qualquer um.
    SECRET_KEY = os.environ.get("SECRET_KEY", "chave-de-desenvolvimento-troque-em-producao")

    # Onde o banco SQLite mora. SQLALCHEMY_TRACK_MODIFICATIONS=False desliga
    # um recurso do SQLAlchemy que a gente não usa (sinalizar toda mudança de
    # objeto) e que só consome memória à toa.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "pulse2050.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Fuso horário usado para interpretar o "HH:MM" das automações e decidir
    # o dia da semana atual (ver services/agendador.py).
    TIMEZONE = os.environ.get("TIMEZONE", "America/Sao_Paulo")

    # Configuração opcional de e-mail (relatório semanal de consumo).
    # Se não configurado, o relatório é apenas gerado e salvo no banco
    # (RelatorioEnviado) em vez de enviado de verdade — ver services/relatorios.py.
    SMTP_HOST = os.environ.get("SMTP_HOST")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER")
    SMTP_SENHA = os.environ.get("SMTP_SENHA")
    SMTP_REMETENTE = os.environ.get("SMTP_REMETENTE", "relatorios@pulse2050.app")
