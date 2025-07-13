from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    abort,
    current_app
)

from flask_login import current_user
from app.models import Utilizador, Anuncio, Categoria
from app import db
from app.utils import admin_required, apagar_imagens_anuncio
from app.forms import CategoriaForm, EditarPerfilForm, CSRFProtecaoForm
from app.models import Mensagem, Favorito, Anuncio
from sqlalchemy import func


bp = Blueprint("admin", __name__)


# region painel ações
@bp.route("/painel")
@admin_required
def painel():
    total_utilizadores = Utilizador.query.count()
    total_anuncios = Anuncio.query.count()
    total_categorias = Categoria.query.count()
    return render_template(
        "admin/painel.html",
        total_utilizadores=total_utilizadores,
        total_anuncios=total_anuncios,
        total_categorias=total_categorias,
    )


# endregion painel ações


# region CRUD utilizadores
@bp.route("/utilizadores")
@admin_required
def gerir_utilizadores():
    pagina = request.args.get("pagina", 1, type=int)
    termo_id = request.args.get("id")
    utilizadores_com_anuncios = (
        db.session.query(Anuncio.utilizador_id).distinct().count()
    )
    total_utilizadores = Utilizador.query.count()
    utilizadores_sem_anuncios = total_utilizadores - utilizadores_com_anuncios
    dados_grafico = {
        "labels": ["Com Anúncios", "Sem Anúncios"],
        "valores": [utilizadores_com_anuncios, utilizadores_sem_anuncios],
    }
    query = Utilizador.query

    if termo_id:
        try:
            termo_id = int(termo_id)
            query = query.filter(Utilizador.id == termo_id)
        except ValueError:
            flash("ID inválido.", "erro")

    utilizadores = query.order_by(Utilizador.data_registo.desc()).paginate(
        page=pagina, per_page=10
    )
    form = CSRFProtecaoForm()
    return render_template(
        "admin/utilizadores.html",
        utilizadores=utilizadores,
        form=form,
        dados_grafico=dados_grafico,
    )


@bp.route("/alterar-papel/<int:id>", methods=["POST"])
@admin_required
def alterar_papel(id):
    utilizador = db.session.get(Utilizador, id)
    if utilizador is None:
        abort(404)

    novo_papel = request.form.get("papel")

    if novo_papel not in ["admin", "utilizador"]:
        flash("Papel inválido", "erro")
        return redirect(url_for("admin.gerir_utilizadores"))

    if utilizador.id == current_user.id and novo_papel != "admin":
        flash("Não pode remover o seu próprio papel de administrador.", "erro")
        return redirect(url_for("admin.gerir_utilizadores"))

    utilizador.papel = novo_papel
    db.session.commit()
    flash(f"Papel de {utilizador.nome} alterado para {novo_papel}", "sucesso")
    return redirect(url_for("admin.gerir_utilizadores"))


@bp.route("/editar-utilizador/<int:id>", methods=["GET", "POST"])
@admin_required
def editar_utilizador(id):
    utilizador = db.session.get(Utilizador, id)
    if utilizador is None:
        abort(404)

    form = EditarPerfilForm(obj=utilizador)
    form.utilizador = utilizador  

    if form.validate_on_submit():
        email_novo = form.email.data.strip().lower()

        # Valida se o email já pertence a outro utilizador
        utilizador_existente = Utilizador.query.filter_by(email=email_novo).first()
        if email_novo != utilizador.email:
            if utilizador_existente and utilizador_existente.id != utilizador.id:
                flash("Este email já está registado por outro utilizador.", "erro")
                return render_template("admin/editar_utilizador.html", form=form, utilizador=utilizador)

        # Só agora aplica as alterações
        utilizador.nome = form.nome.data
        utilizador.email = email_novo

        if form.senha.data:
            utilizador.definir_senha(form.senha.data)

        db.session.commit()
        flash("Utilizador atualizado com sucesso.", "sucesso")
        return redirect(url_for("admin.gerir_utilizadores"))

    return render_template("admin/editar_utilizador.html", form=form, utilizador=utilizador)


@bp.route("/eliminar-utilizador/<int:id>", methods=["POST"])
@admin_required
def eliminar_utilizador(id):
    utilizador = db.session.get(Utilizador, id)
    if utilizador is None:
        abort(404)

    email_utilizador = utilizador.email

    try:
        # Eliminar anúncios e respetivas imagens (caso não uses cascade)
        for anuncio in utilizador.anuncios.all():
            try:
                apagar_imagens_anuncio(anuncio)
            except Exception as e:
                current_app.logger.warning(f"Erro ao apagar imagens do anúncio {anuncio.id}: {e}")
            db.session.delete(anuncio)

        # Apagar o utilizador e dependências (assumindo cascade configurado)
        db.session.delete(utilizador)
        db.session.commit()
        flash(f"Utilizador {email_utilizador} eliminado permanentemente", "sucesso")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao eliminar utilizador {id}: {e}")
        flash("Ocorreu um erro ao eliminar o utilizador.", "erro")

    return redirect(url_for("admin.gerir_utilizadores"))



# endregion CRUD utilizadores


# region painel anuncios
@bp.route("/anuncios")
@admin_required
def gerir_anuncios():
    pagina = request.args.get("pagina", 1, type=int)
    filtro = request.args.get("filtro", "todos")
    vendidos = (
        db.session.query(func.count(Anuncio.id))
        .filter(Anuncio.vendido == True)
        .scalar()
    )
    disponiveis = (
        db.session.query(func.count(Anuncio.id))
        .filter(Anuncio.vendido == False)
        .scalar()
    )

    categorias_data = (
        db.session.query(Categoria.nome, func.count(Anuncio.id))
        .join(Anuncio.categorias)
        .group_by(Categoria.nome)
        .all()
    )
    categorias_labels = [nome for nome, _ in categorias_data]
    categorias_valores = [total for _, total in categorias_data]

    termo_id = request.args.get("id")

    query = Anuncio.query

    if filtro == "eliminados":
        query = query.filter_by(eliminado=True)
    else:
        query = query.filter_by(eliminado=False)

    if termo_id:
        try:
            termo_id = int(termo_id)
            query = query.filter(Anuncio.id == termo_id)
        except ValueError:
            flash("ID inválido.", "erro")

    anuncios = query.order_by(Anuncio.data_criacao.desc()).paginate(
        page=pagina, per_page=10
    )
    form = CSRFProtecaoForm()

    return render_template(
        "admin/anuncios.html",
        anuncios=anuncios,
        filtro=filtro,
        form=form,
        dados_estados={
            "labels": ["Disponíveis", "Vendidos"],
            "valores": [disponiveis, vendidos],
        },
        dados_categorias={"labels": categorias_labels, "valores": categorias_valores},
    )


@bp.route("/restaurar-anuncio/<int:id>", methods=["POST"])
@admin_required
def restaurar_anuncio(id):
    anuncio = db.session.get(Anuncio, id)
    if anuncio is None:
        abort(404)
    anuncio.eliminado = False
    db.session.commit()
    flash("Anúncio restaurado com sucesso", "sucesso")
    return redirect(url_for("admin.gerir_anuncios"))


@bp.route("/eliminar-definitivo/<int:id>", methods=["POST"])
@admin_required
def eliminar_definitivo(id):
    anuncio = db.session.get(Anuncio, id)
    if anuncio is None:
        abort(404)
    db.session.delete(anuncio)
    db.session.commit()
    flash("Anúncio eliminado permanentemente", "sucesso")
    return redirect(url_for("admin.gerir_anuncios"))


# endregion painel anuncios


# region painel categorias
@bp.route("/categorias")
@admin_required
def gerir_categorias():
    categorias = Categoria.query.all()
    form = CategoriaForm()
    return render_template("admin/categorias.html", categorias=categorias, form=form)


@bp.route("/adicionar-categoria", methods=["POST"])
@admin_required
def adicionar_categoria():
    form = CategoriaForm()
    if form.validate_on_submit():
        categoria = Categoria(nome=form.nome.data)
        db.session.add(categoria)
        db.session.commit()
        flash("Categoria criada com sucesso", "sucesso")
    return redirect(url_for("admin.gerir_categorias"))


@bp.route("/eliminar-categoria/<int:id>", methods=["POST"])
@admin_required
def eliminar_categoria(id):
    categoria = db.session.get(Categoria, id)
    if categoria is None:
        abort(404)

    if not categoria:
        flash("Categoria não encontrada.", "danger")
        return redirect(url_for("admin.gerir_categorias"))

    categoria.ativa = False
    db.session.commit()
    flash("Categoria desativada com sucesso.", "success")
    return redirect(url_for("admin.gerir_categorias"))


# endregion painel categorias

#region moderação mensagens

@bp.route("/mensagens/<int:id1>/<int:id2>")
@admin_required
def ver_conversa_entre_utilizadores(id1, id2):
    utilizador1 = db.session.get(Utilizador, id1) or abort(404)
    utilizador2 = db.session.get(Utilizador, id2) or abort(404)

    mensagens = (
        Mensagem.query.filter(
            ((Mensagem.remetente_id == id1) & (Mensagem.destinatario_id == id2)) |
            ((Mensagem.remetente_id == id2) & (Mensagem.destinatario_id == id1))
        )
        .order_by(Mensagem.data_envio.asc())
        .all()
    )

    return render_template(
        "admin/ver_conversa.html",
        utilizador1=utilizador1,
        utilizador2=utilizador2,
        mensagens=mensagens,
    )

#endregion moderação mensagens

