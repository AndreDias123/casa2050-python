from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from models import Usuario

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        senha = request.form.get("senha") or ""

        if not email or not senha:
            flash("Preencha usuário e senha.", "erro")
            return render_template("login.html")

        usuario = Usuario.query.filter_by(email=email).first()
        if usuario is None or not usuario.checar_senha(senha):
            flash("Usuário ou senha inválidos.", "erro")
            return render_template("login.html")

        login_user(usuario, remember=bool(request.form.get("lembrar")))
        return redirect(url_for("main.dashboard"))

    return render_template("login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
