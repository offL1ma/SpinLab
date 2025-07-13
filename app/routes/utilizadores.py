from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    current_app,
    request,
)
from flask_login import login_required, current_user
from app.forms import EditarPerfilForm, CSRFProtecaoForm
from app.models import Favorito, Anuncio, Mensagem, Utilizador
from app.utils import apagar_imagens_anuncio
from app import db
from app.forms import CSRFProtecaoForm
from uuid import uuid4
import os
from werkzeug.utils import secure_filename


bp = Blueprint("utilizadores", __name__)


# region dados perfil
@bp.route("/perfil")
@login_required
def perfil():

    form = CSRFProtecaoForm()
    return render_template("utilizadores/perfil.html", form=form)


# endregion dados perfil


# region editar perfil
@bp.route("/editar-perfil", methods=["GET", "POST"])
@login_required
def editar_perfil():
    form = EditarPerfilForm(obj=current_user)
    form.utilizador = current_user  

    if form.validate_on_submit():
        utilizador_existente = Utilizador.query.filter_by(email=form.email.data).first()
        if form.email.data != current_user.email and utilizador_existente and utilizador_existente.id != current_user.id:
            flash("Este email já está registado por outro utilizador.", "erro")
            return render_template("utilizadores/editar_perfil.html", form=form)

        current_user.nome = form.nome.data
        current_user.email = form.email.data

        # Remoção da foto atual (checkbox ou botão no formulário)
        if request.form.get("remover_foto") == "1":
            if current_user.foto_perfil:
                caminho_antigo = os.path.join(
                    current_app.root_path,
                    "static/uploads/perfis",
                    current_user.foto_perfil,
                )
                if os.path.exists(caminho_antigo):
                    os.remove(caminho_antigo)
                current_user.foto_perfil = None

        # Upload de nova foto
        if form.foto.data:
            imagem = form.foto.data

            # Verifica extensão
            nome = imagem.filename.lower()
            if not nome.endswith((".jpg", ".jpeg", ".png", ".webp")):
                flash("A imagem deve ser JPG, PNG ou WEBP.", "erro")
                return render_template("utilizadores/editar_perfil.html", form=form)

            # Verifica tamanho
            imagem.stream.seek(0, os.SEEK_END)
            tamanho = imagem.stream.tell()
            imagem.stream.seek(0)
            if tamanho > 3 * 1024 * 1024:
                flash("A imagem excede o tamanho máximo de 3MB.", "erro")
                return render_template("utilizadores/editar_perfil.html", form=form)

            # Remove imagem anterior
            if current_user.foto_perfil:
                caminho_antigo = os.path.join(
                    current_app.root_path,
                    "static/uploads/perfis",
                    current_user.foto_perfil,
                )
                if os.path.exists(caminho_antigo):
                    os.remove(caminho_antigo)

            # Guarda nova imagem
            nome_seguro = secure_filename(f"{uuid4().hex}_{imagem.filename}")
            upload_path = os.path.join(current_app.root_path, "static/uploads/perfis")
            os.makedirs(upload_path, exist_ok=True)
            imagem.save(os.path.join(upload_path, nome_seguro))
            current_user.foto_perfil = nome_seguro

        # Alteração de senha (se fornecida)
        if form.senha.data:
            if form.senha.data != form.confirmar_senha.data:
                flash("As senhas não coincidem.", "erro")
                return render_template("utilizadores/editar_perfil.html", form=form)
            current_user.definir_senha(form.senha.data)

        db.session.commit()
        flash("Perfil atualizado com sucesso.", "sucesso")
        return redirect(url_for("utilizadores.perfil"))

    return render_template("utilizadores/editar_perfil.html", form=form)


# endregion editar perfil


# region favoritos
@bp.route("/favoritos")
@login_required
def favoritos():
    form = CSRFProtecaoForm()
    pagina = request.args.get("pagina", 1, type=int)
    favoritos = (
        current_user.favoritos.join(Anuncio)
        .filter(Anuncio.eliminado == False)
        .paginate(page=pagina, per_page=9)
    )

    return render_template(
        "utilizadores/favoritos.html", favoritos=favoritos, form=form
    )


# endregion favoritos


# region remover dos favoritos
@bp.route("/favoritos/remover/<int:anuncio_id>", methods=["POST"])
@login_required
def remover_favorito(anuncio_id):
    favorito = Favorito.query.filter_by(
        utilizador_id=current_user.id, anuncio_id=anuncio_id
    ).first()

    if favorito:
        db.session.delete(favorito)
        db.session.commit()
        flash("Removido dos favoritos", "sucesso")

    return redirect(url_for("utilizadores.favoritos"))


# endregion remover dos favoritos


# region anuncios do utilizador
@bp.route("/meus-anuncios")
@login_required
def meus_anuncios():
    pagina = request.args.get("pagina", 1, type=int)
    anuncios = (
        Anuncio.query.filter_by(utilizador_id=current_user.id, eliminado=False)
        .order_by(Anuncio.data_criacao.desc())
        .paginate(page=pagina, per_page=9)
    )

    return render_template("utilizadores/meus_anuncios.html", anuncios=anuncios)


# endregion anuncios do utilizador


# region eliminar conta
@bp.route("/eliminar-conta", methods=["POST"])
@login_required
def eliminar_conta():
    utilizador = current_user

    Mensagem.query.filter(
        (Mensagem.remetente_id == utilizador.id)
        | (Mensagem.destinatario_id == utilizador.id)
    ).delete(synchronize_session=False)

    Favorito.query.filter_by(utilizador_id=utilizador.id).delete(
        synchronize_session=False
    )

    anuncios = utilizador.anuncios.all()
    anuncio_ids = [anuncio.id for anuncio in anuncios]

    if anuncio_ids:
        Favorito.query.filter(Favorito.anuncio_id.in_(anuncio_ids)).delete(
            synchronize_session=False
        )
        Mensagem.query.filter(Mensagem.anuncio_id.in_(anuncio_ids)).delete(
            synchronize_session=False
        )

    for anuncio in anuncios:
        apagar_imagens_anuncio(anuncio)
        db.session.delete(anuncio)

    db.session.delete(utilizador)
    db.session.commit()

    flash("Conta eliminada com sucesso.", "sucesso")
    return redirect(url_for("auth.logout"))


# endregion eliminar conta
