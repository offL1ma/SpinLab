from functools import wraps
from flask import redirect, url_for, flash, current_app
from flask_login import current_user
from app.models import Anuncio, Tag
import os
from app import db
import json


# region verifica se e admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.papel != "admin":
            return redirect(url_for("anuncios.listar"))
        return f(*args, **kwargs)

    return decorated_function


# endregion verifica se e admin


# region verifica se e dono anuncio
def dono_anuncio_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        anuncio_id = kwargs.get("id")
        anuncio = db.session.get(Anuncio, anuncio_id)
        if not anuncio or (
            anuncio.utilizador_id != current_user.id and current_user.papel != "admin"
        ):
            flash("Não tem permissão para aceder a este anúncio.", "erro")
            return redirect(url_for("anuncios.listar"))
        return f(*args, **kwargs)

    return decorated_function


# endregion verifica se e dono anuncio


# region verifica se imagem e valida
def validar_imagens_upload(files, limite=5):
    """Valida e devolve uma lista de nomes de ficheiros válidos a partir de um conjunto de ficheiros."""
    imagens_validadas = []

    for f in files:
        if f and getattr(f, "filename", "").strip() != "":
            nome = f.filename.lower()
            if not nome.endswith((".jpg", ".jpeg", ".png", ".webp")):
                flash(
                    f"{f.filename} não é um tipo de imagem suportado (JPG, PNG, WEBP).",
                    "erro",
                )
                return None

            f.stream.seek(0, os.SEEK_END)
            tamanho = f.stream.tell()
            f.stream.seek(0)

            if tamanho > 3 * 1024 * 1024:
                flash(f"{f.filename} excede o tamanho máximo de 3MB.", "erro")
                return None

            imagens_validadas.append(f)

    if not imagens_validadas:
        flash("É necessário enviar pelo menos uma imagem válida.", "erro")
        return None

    if len(imagens_validadas) > limite:
        flash(f"Pode enviar no máximo {limite} imagens.", "erro")
        return None

    return imagens_validadas


# endregion verifica se imagem e valida


# region apaga imagem do anuncio
def apagar_imagens_anuncio(anuncio):
    for img in anuncio.imagens:
        caminho = os.path.join("app/static/uploads", img.nome_arquivo)
        try:
            if os.path.exists(caminho):
                os.remove(caminho)
                current_app.logger.info(f"Imagem apagada: {img.nome_arquivo}")
            else:
                current_app.logger.warning(f"Imagem não encontrada: {img.nome_arquivo}")
        except Exception as e:
            current_app.logger.error(f"Erro ao apagar imagem {img.nome_arquivo}: {e}")



# endregion apaga imagem do anuncio


# region transforma tags em formato json para strings
def transformar_tags(input_raw):

    # Recebe uma string (simples ou JSON) de tags e devolve uma lista de instâncias Tag.
    # Cria novas tags se não existirem.

    tag_names = []

    try:
        tags_json = json.loads(input_raw)
        if isinstance(tags_json, list):
            tag_names = [
                t["value"].strip().lower()
                for t in tags_json
                if isinstance(t, dict) and "value" in t
            ]
    except (ValueError, TypeError):
        tag_names = [t.strip().lower() for t in input_raw.split(",") if t.strip()]

    tags = []
    for nome in tag_names:
        tag = Tag.query.filter_by(nome=nome).first()
        if not tag:
            tag = Tag(nome=nome)
            db.session.add(tag)
        tags.append(tag)

    return tags


# endregion transforma tags em formato json para strings

#region validar valor min e max pesquisa

def aplicar_filtro_preco(query, min_preco, max_preco):
    try:
        min_val = float(min_preco) if min_preco else None
        max_val = float(max_preco) if max_preco else None

        if min_val is not None and max_val is not None:
            if min_val > max_val:
                flash("O preço mínimo não pode ser superior ao preço máximo.", "warning")
                return query
            return query.filter(Anuncio.preco >= min_val, Anuncio.preco <= max_val)
        elif min_val is not None:
            return query.filter(Anuncio.preco >= min_val)
        elif max_val is not None:
            return query.filter(Anuncio.preco <= max_val)

    except ValueError:
        flash("Os valores de preço inseridos são inválidos.", "warning")
    return query
#endregion validar valor min e max pesquisa