from flask import Blueprint, render_template, redirect, url_for, flash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import login_user, logout_user, current_user
from app.forms import RegistoForm, LoginForm
from app.models import Utilizador
from app import db

bp = Blueprint("auth", __name__)
limiter = Limiter(key_func=get_remote_address)


# region criar conta
@bp.route("/registo", methods=["GET", "POST"])
def registo():
    if current_user.is_authenticated:
        return redirect(url_for("anuncios.listar"))

    form = RegistoForm()
    if form.validate_on_submit():
        utilizador = Utilizador(nome=form.nome.data, email=form.email.data)
        utilizador.definir_senha(form.senha.data)
        db.session.add(utilizador)
        db.session.commit()
        login_user(utilizador)
        flash("Conta criada com sucesso! Bem vindo(a)", "sucesso")
        return redirect(url_for("anuncios.listar"))


    return render_template("auth/registo.html", form=form)


# endregion criar conta


# region login
@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("anuncios.listar"))

    form = LoginForm()
    if form.validate_on_submit():
        utilizador = Utilizador.query.filter_by(email=form.email.data).first()
        if utilizador and utilizador.verificar_senha(form.senha.data):
            login_user(utilizador)

            if utilizador.papel == "admin":
                return redirect(url_for("admin.painel"))
            return redirect(url_for("anuncios.listar"))

        flash(f"Email ou senha incorretos para: {form.email.data}", "erro")

    return render_template("auth/login.html", form=form)


# endregion login


# region sair/logout
@bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("anuncios.listar"))


# endregion sair/logout
