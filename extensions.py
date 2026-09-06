"""Instâncias das extensões Flask, separadas em módulo próprio para evitar
importação circular entre app.py, models.py e as blueprints."""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
# Se alguém sem login tentar acessar uma rota marcada com @login_required, o
# Flask-Login redireciona pra essa rota (login_view) e mostra essa mensagem.
login_manager.login_view = "auth.login"
login_manager.login_message = "Faça login para acessar a PULSE2050."
