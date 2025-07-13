from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    current_app,
    abort,
    jsonify,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.forms import AnuncioForm, CSRFProtecaoForm, ComentarioForm
from app.models import Anuncio, Categoria, Favorito, AnuncioImagem, Tag
from app import db
from sqlalchemy import or_, String, select
from app.models import anuncio_categoria, Favorito, Comentario
from app.utils import dono_anuncio_required, admin_required, transformar_tags
from datetime import datetime, timedelta, UTC
import os
from app.utils import validar_imagens_upload, apagar_imagens_anuncio, aplicar_filtro_preco
from uuid import uuid4
import json


bp = Blueprint("anuncios", __name__)


# region Listar anuncios(HOME))
@bp.route("/")
def listar():
    pagina = request.args.get("pagina", 1, type=int)
    pesquisa = request.args.get("pesquisa", "")
    categoria_ids = request.args.getlist("categorias")
    min_preco = request.args.get("min_preco")
    max_preco = request.args.get("max_preco")
    ano = request.args.get("ano")
    estado = request.args.get("estado")
    formato = request.args.get("formato")
    ordenar = request.args.get("ordenar")
    tag_nome = request.args.get("tag")

    query = Anuncio.query.filter(Anuncio.eliminado == False, Anuncio.vendido == False)

    if categoria_ids:
        query = query.join(anuncio_categoria).filter(
            anuncio_categoria.c.categoria_id.in_(categoria_ids)
        )

    if pesquisa:
        query = query.filter(
            or_(
                Anuncio.titulo.ilike(f"%{pesquisa}%"),
                Anuncio.artista.ilike(f"%{pesquisa}%"),
                Anuncio.descricao.ilike(f"%{pesquisa}%"),
                Anuncio.formato.ilike(f"%{pesquisa}%"),
                Anuncio.ano.cast(String).ilike(f"%{pesquisa}%"),
            )
        )
    if tag_nome:
        query = query.join(Anuncio.tags).filter(Tag.nome.ilike(f"%{tag_nome}%"))

    if categoria_ids:
        query = query.filter(anuncio_categoria.c.categoria_id.in_(categoria_ids))

    query = aplicar_filtro_preco(query, min_preco, max_preco)


    if ano:
        query = query.filter(Anuncio.ano == int(ano))

    if formato:
        query = query.filter(Anuncio.formato == formato)
    if estado:
        query = query.filter(Anuncio.estado == estado)

    # Ordenação
    if ordenar == "preco_asc":
        query = query.order_by(Anuncio.preco.asc())
    elif ordenar == "preco_desc":
        query = query.order_by(Anuncio.preco.desc())
    elif ordenar == "mais_recentes":
        query = query.order_by(Anuncio.data_criacao.desc())
    else:
        query = query.order_by(Anuncio.data_criacao.desc())

    query = query.filter(Anuncio.vendido == False)

    anuncios = query.paginate(page=pagina, per_page=10, error_out=False)

    categorias = Categoria.query.all()
    return render_template(
        "anuncios/listar.html",
        anuncios=anuncios,
        categorias=categorias,
        filtros=request.args,
    )


# endregion Listar anuncios(HOME)


# region Criar anuncio
@bp.route("/criar", methods=["GET", "POST"])
@login_required
def criar():
    form = AnuncioForm()
    categorias = db.session.scalars(
        select(Categoria).where(Categoria.ativa == True)
    ).all()
    form.categorias.choices = [(c.id, c.nome) for c in categorias]

    if form.validate_on_submit():
        with db.session.no_autoflush:
            upload_dir = os.path.join(current_app.root_path, "static", "uploads")
            os.makedirs(upload_dir, exist_ok=True)

            imagens_validas = validar_imagens_upload(form.imagens.data)

            if not imagens_validas or len(imagens_validas) == 0:
                flash("É necessário enviar pelo menos uma imagem válida.", "erro")
                return render_template("anuncios/criar.html", form=form)

            imagens_salvas = []
            for f in imagens_validas:
                nome = secure_filename(f"{uuid4().hex}_{f.filename}")
                caminho = os.path.join(upload_dir, nome)
                f.save(caminho)
                imagens_salvas.append(nome)

            if len(imagens_salvas) == 0:
                flash("Erro inesperado: Nenhuma imagem foi salva.", "erro")
                return render_template("anuncios/criar.html", form=form)

            anuncio = Anuncio(
                titulo=form.titulo.data,
                artista=form.artista.data,
                ano=form.ano.data,
                preco=form.preco.data,
                descricao=form.descricao.data,
                formato=form.formato.data,
                dimensoes_cm=form.get_dimensoes_string(),
                imagem=imagens_salvas[0],
                estado=form.estado.data,
                eliminado=False,
                vendido=False,
                criador=current_user,
            )

            anuncio.tags = transformar_tags(form.tags.data)

            categoria_ids = form.categorias.data
            categorias = [
                db.session.get(Categoria, cid) for cid in categoria_ids if cid
            ]

            for categoria in categorias:
                if categoria:
                    anuncio.categorias.append(categoria)

            db.session.add(anuncio)
            db.session.flush()

            for nome in imagens_salvas:
                db.session.add(AnuncioImagem(anuncio_id=anuncio.id, nome_arquivo=nome))

            if not anuncio.imagem:
                imagens_restantes = list(anuncio.imagens)
                if imagens_restantes:
                    anuncio.imagem = imagens_restantes[0].nome_arquivo
                else:
                    flash("Erro: nenhuma imagem atribuída.", "erro")
                    return render_template("anuncios/criar.html", form=form)

        db.session.commit()
        flash("Anúncio criado com sucesso!", "sucesso")
        return redirect(url_for("anuncios.detalhes", id=anuncio.id))

    return render_template("anuncios/criar.html", form=form)


# endregion Criar anuncio


# region Detalhes do anuncio
@bp.route("/<int:id>", methods=["GET", "POST"])
@login_required
def detalhes(id):
    anuncio = db.session.get(Anuncio, id) or abort(404)
    form = ComentarioForm()
    csrf = CSRFProtecaoForm()

    if form.validate_on_submit():
        comentario = Comentario(
            conteudo=form.conteudo.data,
            utilizador_id=current_user.id,
            anuncio_id=anuncio.id,
        )
        db.session.add(comentario)
        db.session.commit()
        flash("Comentário publicado com sucesso!", "success")
        return redirect(url_for("anuncios.detalhes", id=id))

    comentarios = (
        Comentario.query.filter_by(anuncio_id=anuncio.id)
        .order_by(Comentario.data.desc())
        .all()
    )

    return render_template(
        "anuncios/detalhes.html",
        anuncio=anuncio,
        form=form,
        comentarios=comentarios,
        csrf=csrf,
    )


# endregion Detalhes do anuncio


# region editar o anuncio
@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@dono_anuncio_required
def editar(id):
    anuncio = db.session.get(Anuncio, id) or abort(404)
    form = AnuncioForm(obj=anuncio)

    imagem_removida_principal = False  # ← Garantimos que sempre existe

    # Pré-preenchimento das dimensões
    if request.method == "GET":
        form.categorias.data = [cat.id for cat in anuncio.categorias]
        if anuncio.dimensoes_cm:
            try:
                partes = anuncio.dimensoes_cm.replace(" cm", "").split("x")
                form.altura_cm.data = float(partes[0])
                form.largura_cm.data = float(partes[1])
                form.profundidade_cm.data = float(partes[2])
            except (ValueError, IndexError):
                pass

        form.tags.data = ", ".join(tag.nome for tag in anuncio.tags)

    if form.validate_on_submit():
        with db.session.no_autoflush:
            # Remover imagens persistentes marcadas
            ids_para_remover = request.form.get("remover_imagens")
            if ids_para_remover:
                ids = [int(i) for i in ids_para_remover.split(",") if i.isdigit()]
                for img_id in ids:
                    img = db.session.get(AnuncioImagem, img_id)
                    if img and img.anuncio_id == anuncio.id:
                        if img.nome_arquivo == anuncio.imagem:
                            imagem_removida_principal = True
                        caminho = os.path.join(
                            current_app.config["UPLOAD_FOLDER"], img.nome_arquivo
                        )
                        if os.path.exists(caminho):
                            os.remove(caminho)
                        db.session.delete(img)

            # Validar novas imagens
            ids_remover = set(
                int(i)
                for i in request.form.get("remover_imagens", "").split(",")
                if i.isdigit()
            )
            imagens_existentes = sum(
                1 for img in anuncio.imagens if img.id not in ids_remover
            )

            imagens_validas = validar_imagens_upload(
                form.imagens.data, limite=5 - imagens_existentes
            )
            total_imagens_novas = len(imagens_validas) if imagens_validas else 0

            if imagens_existentes + total_imagens_novas == 0:
                flash(
                    "O anúncio precisa de pelo menos uma imagem (nova ou já existente).",
                    "erro",
                )
                return render_template(
                    "anuncios/editar.html", form=form, anuncio=anuncio
                )

            imagens_salvas = []
            if imagens_validas:
                upload_dir = os.path.join(current_app.root_path, "static", "uploads")
                os.makedirs(upload_dir, exist_ok=True)

                for f in imagens_validas:
                    nome = secure_filename(f"{uuid4().hex}_{f.filename}")
                    caminho = os.path.join(upload_dir, nome)
                    f.save(caminho)
                    imagens_salvas.append(nome)

                for nome in imagens_salvas:
                    db.session.add(
                        AnuncioImagem(anuncio_id=anuncio.id, nome_arquivo=nome)
                    )

        db.session.flush()

        if imagem_removida_principal or not anuncio.imagem:
            imagens_restantes = (
                db.session.query(AnuncioImagem).filter_by(anuncio_id=anuncio.id).all()
            )
            if imagens_restantes:
                anuncio.imagem = imagens_restantes[0].nome_arquivo
            else:
                flash("O anúncio precisa de pelo menos uma imagem.", "erro")
                return render_template(
                    "anuncios/editar.html", form=form, anuncio=anuncio
                )

        # Atualizar os campos do anúncio
        anuncio.titulo = form.titulo.data
        anuncio.artista = form.artista.data
        anuncio.ano = form.ano.data
        anuncio.preco = form.preco.data
        anuncio.descricao = form.descricao.data
        anuncio.formato = form.formato.data
        anuncio.estado = form.estado.data
        anuncio.dimensoes_cm = form.get_dimensoes_string()
        categorias_ativas = db.session.scalars(
            select(Categoria).where(
                Categoria.id.in_(form.categorias.data), Categoria.ativa == True
            )
        ).all()

        categorias_inativas_mantidas = [
            cat
            for cat in anuncio.categorias
            if cat.id in form.categorias.data and not cat.ativa
        ]

        anuncio.categorias = categorias_ativas + categorias_inativas_mantidas
        anuncio.tags = transformar_tags(form.tags.data)

        db.session.commit()
        flash("Anúncio atualizado com sucesso!", "sucesso")
        return redirect(url_for("anuncios.detalhes", id=anuncio.id))

    return render_template("anuncios/editar.html", form=form, anuncio=anuncio)


# endregion editar o anuncio


# region mover para eliminados
@bp.route("/<int:id>/eliminar", methods=["POST"])
@dono_anuncio_required
def eliminar(id):
    anuncio = db.session.get(Anuncio, id) or abort(404)
    anuncio.eliminado = True
    db.session.commit()
    flash("Anúncio movido para eliminados.", "info")
    return redirect(url_for("utilizadores.meus_anuncios"))


# endregion mover para eliminados


# region favoritos
@bp.route("/<int:id>/favorito", methods=["POST"])
@login_required
def toggle_favorito(id):
    anuncio = db.session.get(Anuncio, id) or abort(404)

    if anuncio.utilizador_id == current_user.id:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"erro": "Não pode favoritar o seu próprio anúncio."}), 403
        flash("Não pode favoritar o seu próprio anúncio.", "aviso")
        return redirect(url_for("anuncios.detalhes", id=id))

    favorito = Favorito.query.filter_by(
        utilizador_id=current_user.id, anuncio_id=id
    ).first()

    if favorito:
        db.session.delete(favorito)
        db.session.commit()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"status": "removido"})
        flash("Removido dos favoritos", "info")
    else:
        novo_favorito = Favorito(utilizador_id=current_user.id, anuncio_id=id)
        db.session.add(novo_favorito)
        db.session.commit()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"status": "adicionado"})
        flash("Adicionado aos favoritos", "sucesso")
    return redirect(request.referrer or url_for("anuncios.detalhes", id=id))


def favoritos():
    pagina = request.args.get("pagina", 1, type=int)
    favoritos = Favorito.query.filter_by(utilizador_id=current_user.id).paginate(
        page=pagina, per_page=10
    )
    return render_template("utilizadores/favoritos.html", favoritos=favoritos)


# endregion favoritos


# region eliminar permanente
@bp.route("/<int:id>/eliminar-definitivo", methods=["POST"])
@login_required
@dono_anuncio_required
def eliminar_definitivo(id):
    anuncio = db.session.get(Anuncio, id) or abort(404)
    apagar_imagens_anuncio(anuncio)
    db.session.delete(anuncio)
    db.session.commit()
    flash("Anúncio eliminado permanentemente.", "sucesso")
    return redirect(url_for("anuncios.lixeira"))


# endregion eliminar permanente


# region marcar vendido
@bp.route("/<int:id>/marcar-vendido", methods=["POST"])
@login_required
def marcar_vendido(id):
    anuncio = db.session.get(Anuncio, id) or abort(404)
    if anuncio.criador != current_user and current_user.papel != "admin":
        abort(403)
    anuncio.vendido = not anuncio.vendido
    anuncio.estado = "vendido" if anuncio.vendido else "disponivel"
    db.session.commit()
    flash("Estado atualizado com sucesso.", "sucesso")
    return redirect(url_for("anuncios.detalhes", id=id))


# endregion marcar vendido


# region limpar anuncios antigos
@bp.route("/limpar-antigos")
@admin_required
def limpar_anuncios_antigos():
    prazo = datetime.now(UTC) - timedelta(days=7)
    antigos = db.session.scalars(
        select(Anuncio).filter_by(eliminado=True).filter(Anuncio.data_criacao < prazo)
    ).all()
    total = len(antigos)
    for anuncio in antigos:
        db.session.delete(anuncio)
    db.session.commit()
    flash(f"{total} anúncio(s) antigos eliminados permanentemente.", "sucesso")
    return redirect(url_for("admin.gerir_anuncios"))


# endregion limpar anuncios antigos


# region lixeira (user)
@bp.route("/meus-anuncios/lixeira")
@login_required
def lixeira():
    pagina = request.args.get("pagina", 1, type=int)
    anuncios = (
        Anuncio.query.filter_by(utilizador_id=current_user.id, eliminado=True)
        .order_by(Anuncio.data_criacao.desc())
        .paginate(page=pagina, per_page=10, error_out=False)
    )
    return render_template("utilizadores/lixeira.html", anuncios=anuncios)


# endregion lixeira (user)


# region restaurar anuncio
@bp.route("/<int:id>/restaurar", methods=["POST"])
@login_required
def restaurar(id):
    anuncio = db.session.get(Anuncio, id) or abort(404)
    if anuncio.criador != current_user and current_user.papel != "admin":
        abort(403)
    anuncio.eliminado = False
    db.session.commit()
    flash("Anúncio restaurado com sucesso!", "sucesso")
    return redirect(url_for("anuncios.detalhes", id=id))


# endregion restaurar anuncio
# region eliminar comentario
@bp.route("/comentario/<int:id>/eliminar", methods=["POST"])
@login_required
def eliminar_comentario(id):
    comentario = db.session.get(Comentario, id) or abort(404)

    if current_user != comentario.utilizador and current_user.papel != "admin":
        abort(403)

    db.session.delete(comentario)
    db.session.commit()
    flash("Comentário eliminado.", "success")
    return redirect(url_for("anuncios.detalhes", id=comentario.anuncio_id))


# endregion eliminar comentario
