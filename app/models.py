from datetime import datetime, UTC
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, login_manager
from app import db
from sqlalchemy.orm import relationship

# region Tabela intermediária Anúncio-Categoria
anuncio_categoria = db.Table(
    "anuncio_categoria",
    db.Column("anuncio_id", db.Integer, db.ForeignKey("anuncios.id"), primary_key=True),
    db.Column(
        "categoria_id", db.Integer, db.ForeignKey("categorias.id"), primary_key=True
    ),
)
# endregion Tabela intermediária Anúncio-Categoria


# region utilizador
class Utilizador(UserMixin, db.Model):
    __tablename__ = "utilizadores"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(128), nullable=False)
    papel = db.Column(db.String(20), default="utilizador")
    foto_perfil = db.Column(db.String(200), nullable=True)
    data_registo = db.Column(db.DateTime, default=datetime.now(UTC))

    anuncios = db.relationship("Anuncio", backref="criador", lazy="dynamic", cascade="all, delete-orphan")

    favoritos = db.relationship("Favorito", backref="utilizador", lazy="dynamic", cascade="all, delete-orphan")

    mensagens_enviadas = db.relationship(
        "Mensagem",
        foreign_keys="Mensagem.remetente_id",
        backref="remetente",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    mensagens_recebidas = db.relationship(
        "Mensagem",
        foreign_keys="Mensagem.destinatario_id",
        backref="destinatario",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    comentarios = db.relationship(
        "Comentario",
        backref="utilizador",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)


# endregion utilizador


# region categoria anuncios
class Categoria(db.Model):
    __tablename__ = "categorias"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    ativa = db.Column(db.Boolean, default=True)


# endregion categoria anuncios

# region relacional tag-anuncio

anuncio_tag = db.Table(
    "anuncio_tag",
    db.Column("anuncio_id", db.Integer, db.ForeignKey("anuncios.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
)
# endregion relacional tag-anuncio
# region TAGS de anuncios


class Tag(db.Model):
    __tablename__ = "tags"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    anuncios = db.relationship("Anuncio", secondary=anuncio_tag, back_populates="tags")


# endregion TAGS de anuncios


# region anuncios
class Anuncio(db.Model):
    __tablename__ = "anuncios"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    artista = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    preco = db.Column(db.Float, nullable=False)
    ano = db.Column(db.Integer, nullable=True)
    formato = db.Column(db.String(50), nullable=False)
    dimensoes_cm = db.Column(db.String(50), nullable=True)
    estado = db.Column(db.String(50), nullable=False)
    imagem = db.Column(db.String(200), nullable=False)
    eliminado = db.Column(db.Boolean, default=False)
    data_criacao = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    utilizador_id = db.Column(db.Integer, db.ForeignKey("utilizadores.id"))
    vendido = db.Column(db.Boolean, default=False, nullable=False)
    favoritos = db.relationship(
        "Favorito", back_populates="anuncio", cascade="all, delete-orphan"
    )

    categorias = db.relationship(
        "Categoria", secondary=anuncio_categoria, backref="anuncios"
    )
    imagens = db.relationship("AnuncioImagem", backref="anuncio", lazy="dynamic", cascade="all, delete-orphan")
    mensagens = db.relationship("Mensagem", backref="anuncio", lazy="dynamic", cascade="all, delete-orphan")
    tags = db.relationship("Tag", secondary=anuncio_tag, back_populates="anuncios")

    comentarios = db.relationship(
    "Comentario",
    backref="anuncio",
    lazy="dynamic",
    cascade="all, delete-orphan"
    )


# endregion anuncios


# region imagem anuncios
class AnuncioImagem(db.Model):
    __tablename__ = "anuncio_imagens"
    id = db.Column(db.Integer, primary_key=True)
    nome_arquivo = db.Column(db.String(200), nullable=False)
    anuncio_id = db.Column(db.Integer, db.ForeignKey("anuncios.id"))


# endregion imagem anuncios


# region favorito anuncios
class Favorito(db.Model):
    __tablename__ = "favoritos"
    utilizador_id = db.Column(
        db.Integer, db.ForeignKey("utilizadores.id"), primary_key=True
    )
    anuncio_id = db.Column(
        db.Integer, db.ForeignKey("anuncios.id", ondelete="CASCADE"), primary_key=True
    )

    data_adicao = db.Column(db.DateTime, default=datetime.now(UTC))

    anuncio = db.relationship("Anuncio", back_populates="favoritos")


# endregion favorito anuncios


# region mensagem anuncios
class Mensagem(db.Model):
    __tablename__ = "mensagens"
    id = db.Column(db.Integer, primary_key=True)
    assunto = db.Column(db.String(200), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    data_envio = db.Column(db.DateTime, default=datetime.now(UTC))
    lida = db.Column(db.Boolean, default=False)
    remetente_id = db.Column(db.Integer, db.ForeignKey("utilizadores.id"))
    destinatario_id = db.Column(db.Integer, db.ForeignKey("utilizadores.id"))
    anuncio_id = db.Column(db.Integer, db.ForeignKey("anuncios.id"))


@login_manager.user_loader
def load_user(id):
    return db.session.get(Utilizador, int(id))


# endregion mensagem anuncios


# region comentarios
class Comentario(db.Model):
    __tablename__ = "comentarios"

    id = db.Column(db.Integer, primary_key=True)
    conteudo = db.Column(db.Text, nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)

    utilizador_id = db.Column(
        db.Integer, db.ForeignKey("utilizadores.id"), nullable=False
    )
    anuncio_id = db.Column(db.Integer, db.ForeignKey("anuncios.id"), nullable=False)


# endregion comentarios
