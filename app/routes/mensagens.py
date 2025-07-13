from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.models import Mensagem, Utilizador, Anuncio
from app.forms import MensagemForm
from app import db
from app.utils import admin_required


bp = Blueprint("mensagens", __name__)


# region enviar mensagen
@bp.route("/enviar/<int:destinatario_id>", methods=["GET", "POST"])
@login_required
def enviar_mensagem(destinatario_id):
    destinatario = db.session.get(Utilizador, destinatario_id) or abort(404)
    anuncio_id = request.args.get("anuncio_id")

    if destinatario_id == current_user.id:
        flash("Não pode enviar mensagem para si mesmo.", "erro")
        if anuncio_id:
            try:
                return redirect(url_for("anuncios.detalhes", id=int(anuncio_id)))
            except ValueError:
                return redirect(url_for("anuncios.listar"))
        return redirect(url_for("anuncios.listar"))

    form = MensagemForm()

    if form.validate_on_submit():
        try:
            anuncio_id_int = int(anuncio_id) if anuncio_id else None
        except ValueError:
            anuncio_id_int = None

        mensagem = Mensagem(
            assunto=form.assunto.data,
            conteudo=form.conteudo.data,
            remetente=current_user,
            destinatario=destinatario,
            anuncio_id=anuncio_id_int,
        )
        db.session.add(mensagem)
        db.session.commit()
        flash("Mensagem enviada com sucesso!", "sucesso")
        return redirect(url_for("mensagens.caixa_entrada"))

    if anuncio_id:
        try:
            anuncio = db.session.get(Anuncio, int(anuncio_id))
            if anuncio:
                form.assunto.data = f"Interesse no anúncio: {anuncio.titulo}"
        except ValueError:
            pass

    return render_template(
        "mensagens/enviar.html", form=form, destinatario=destinatario
    )


# endregion enviar mensagen


# region caixa entrada
@bp.route("/caixa-entrada")
@login_required
def caixa_entrada():
    pagina = request.args.get("pagina", 1, type=int)

    mensagens_paginadas = (
        Mensagem.query.filter(
            (Mensagem.remetente_id == current_user.id)
            | (Mensagem.destinatario_id == current_user.id)
        )
        .order_by(Mensagem.data_envio.desc())
        .paginate(page=pagina, per_page=10, error_out=False)
    )

    conversas = {}
    for msg in mensagens_paginadas.items:
        parceiro = msg.destinatario if msg.remetente == current_user else msg.remetente
        anuncio_id = msg.anuncio_id or 0
        chave = (parceiro.id, anuncio_id)

        titulo = msg.anuncio.titulo if msg.anuncio else None
        artista = msg.anuncio.artista if msg.anuncio else None

        if chave not in conversas:
            conversas[chave] = (parceiro, [msg], titulo, artista)
        else:
            conversas[chave][1].append(msg)

    return render_template(
        "mensagens/caixa_entrada.html",
        conversas=conversas,
        mensagens=mensagens_paginadas
    )



# endregion caixa entrada


# region marcar vendido
@bp.route("/<int:id>/marcar-vendido", methods=["POST"])
@login_required
def marcar_vendido(id):
    anuncio = db.session.get(Anuncio, id) or abort(404)

    if anuncio.criador != current_user and current_user.papel != "admin":
        abort(403)
    anuncio.estado = "disponivel" if anuncio.estado == "vendido" else "vendido"
    db.session.commit()
    flash("Estado atualizado com sucesso.", "sucesso")
    return redirect(url_for("anuncios.detalhes", id=id))


# endregion marcar vendido


# region conversa
@bp.route("/conversa/<int:utilizador_id>")
@login_required
def conversa(utilizador_id):
    parceiro = db.session.get(Utilizador, utilizador_id) or abort(404)
    anuncio_id = request.args.get("anuncio_id", type=int)

    mensagens_query = Mensagem.query.filter(
        ((Mensagem.remetente_id == current_user.id) & (Mensagem.destinatario_id == parceiro.id)) |
        ((Mensagem.remetente_id == parceiro.id) & (Mensagem.destinatario_id == current_user.id))
    )

    anuncio = None
    if anuncio_id:
        mensagens_query = mensagens_query.filter(Mensagem.anuncio_id == anuncio_id)
        anuncio = db.session.get(Anuncio, anuncio_id)

    mensagens = mensagens_query.order_by(Mensagem.data_envio).all()

    for msg in mensagens:
        if msg.destinatario_id == current_user.id and not msg.lida:
            msg.lida = True
    db.session.commit()

    form = MensagemForm()
    return render_template(
        "mensagens/conversa.html",
        parceiro=parceiro,
        mensagens=mensagens,
        form=form,
        anuncio=anuncio
    )


# endregion conversa


# region mensagem
@bp.route("/mensagem/<int:id>")
@login_required
def ver_mensagem(id):
    mensagem = db.session.get(Mensagem, id) or abort(404)

    if mensagem.destinatario != current_user:
        abort(403)

    if not mensagem.lida:
        mensagem.lida = True
        db.session.commit()

    return render_template("mensagens/ver.html", mensagem=mensagem)


# endregion mensagem


# region responder
@bp.route("/responder/<int:destinatario_id>", methods=["POST"])
@login_required
def responder_mensagem(destinatario_id):
    form = MensagemForm()
    destinatario = db.session.get(Utilizador, destinatario_id) or abort(404)
    anuncio_id = request.args.get("anuncio_id", type=int)

    if form.validate_on_submit():
        mensagem = Mensagem(
            assunto="",
            conteudo=form.conteudo.data,
            remetente=current_user,
            destinatario=destinatario,
            anuncio_id=anuncio_id
        )
        db.session.add(mensagem)
        db.session.commit()
        flash("Mensagem enviada com sucesso!", "sucesso")
        return redirect(url_for("mensagens.conversa", utilizador_id=destinatario_id, anuncio_id=anuncio_id))

    # fallback render se erro de validação
    mensagens = Mensagem.query.filter(
        ((Mensagem.remetente_id == current_user.id) & (Mensagem.destinatario_id == destinatario.id)) |
        ((Mensagem.remetente_id == destinatario.id) & (Mensagem.destinatario_id == current_user.id))
    )
    if anuncio_id:
        mensagens = mensagens.filter(Mensagem.anuncio_id == anuncio_id)

    mensagens = mensagens.order_by(Mensagem.data_envio).all()
    anuncio = db.session.get(Anuncio, anuncio_id) if anuncio_id else None

    return render_template(
        "mensagens/conversa.html", parceiro=destinatario, mensagens=mensagens, form=form, anuncio=anuncio
    )



# endregion responder
