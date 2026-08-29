import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Em produção, defina SECRET_KEY como variável de ambiente.
    SECRET_KEY = os.environ.get("SECRET_KEY", "chave-de-desenvolvimento-troque-em-producao")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "casa2050.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configuração opcional de e-mail (relatório semanal de consumo).
    # Se não configurado, o relatório é apenas gerado e salvo no banco
    # (RelatorioEnviado) em vez de enviado de verdade — ver services/relatorios.py.
    SMTP_HOST = os.environ.get("SMTP_HOST")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER")
    SMTP_SENHA = os.environ.get("SMTP_SENHA")
    SMTP_REMETENTE = os.environ.get("SMTP_REMETENTE", "relatorios@casa2050.app")
