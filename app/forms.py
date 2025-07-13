from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    TextAreaField,
    FloatField,
    IntegerField,
    SubmitField,
    SelectField,
    ValidationError,
    HiddenField,
    SelectMultipleField,
    FileField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    ValidationError,
    EqualTo,
    Optional,
)
from app.models import Utilizador, Categoria
from flask_login import current_user
from wtforms import DecimalField
from wtforms.fields import MultipleFileField
from datetime import datetime
from flask_wtf import FlaskForm
import os


class CSRFProtecaoForm(FlaskForm):
    pass


# region formulario criar conta
class RegistoForm(FlaskForm):
    nome = StringField("Primeiro e último nome", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    senha = PasswordField("Palavra Passe", validators=[DataRequired(), Length(min=6)])
    confirmar_senha = PasswordField(
        "Confirmar Palavra Passe",
        validators=[
            DataRequired(),
            EqualTo("senha", message="As palavras passe não coincidem."),
        ],
    )

    def validate_email(self, field):
        if Utilizador.query.filter_by(email=field.data).first():
            raise ValidationError("Este email já está registado.")


# endregion formulario criar conta


# region formulario login
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    senha = PasswordField("Palavra Passe", validators=[DataRequired()])


# endregion formulario login


# region formulario anuncio
class AnuncioForm(FlaskForm):
    titulo = StringField("Nome do Álbum", validators=[DataRequired(), Length(max=150)])
    artista = StringField("Artista", validators=[DataRequired()])
    ano = IntegerField("Ano", validators=[Optional()])
    preco = FloatField("Preço (€)", validators=[DataRequired()])
    descricao = TextAreaField("Descrição", validators=[Optional()])
    imagens = MultipleFileField("Imagens do artigo (máx. 5)")
    tags = StringField(
        "Tags (separadas por vírgula)", validators=[Optional(), Length(max=200)]
    )

    categorias = SelectMultipleField(
        "Categorias",
        choices=[],
        coerce=int,
        validators=[DataRequired()],
        render_kw={"class": "form-select", "multiple": True, "size": 6},
    )
    formato = SelectField(
        "Formato",
        choices=[
            ("Vinil", "Vinil"),
            ("CD", "CD"),
            ("DVD", "DVD"),
            ("Cassete", "Cassete"),
            ("Outros", "Outros"),
        ],
        validators=[DataRequired()],
    )
    altura_cm = DecimalField("Altura (cm)", places=1, validators=[Optional()])
    largura_cm = DecimalField("Comprimento (cm)", places=1, validators=[Optional()])
    profundidade_cm = DecimalField(
        "Profundidade (cm)", places=1, validators=[Optional()]
    )
    estado = SelectField(
        "Estado",
        choices=[
            ("Novo com embalagens Originais", "Novo com embalagens originais"),
            ("Novo", "Novo"),
            ("Usado em bom estado", "Usado em bom estado"),
            ("Usado", "Usado"),
        ],
        validators=[DataRequired()],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.categorias.choices = [
            (cat.id, cat.nome)
            for cat in Categoria.query.filter_by(ativa=True)
            .order_by(Categoria.nome)
            .all()
        ]

        self.formato.choices = [
            ("Vinil", "Vinil"),
            ("CD", "CD"),
            ("DVD", "DVD"),
            ("Cassete", "Cassete"),
            ("Outros", "Outros"),
        ]

        self.estado.choices = [
            ("Novo com embalagens Originais", "Novo com embalagens originais"),
            ("Novo", "Novo"),
            ("Usado em bom estado", "Usado em bom estado"),
            ("Usado", "Usado"),
        ]

    def validate_ano(self, field):
        if field.data < 1900 or field.data > datetime.now().year:
            raise ValidationError("Ano inválido.")

    def validate_imagens(self, field):
        imagens = [
            img
            for img in field.data
            if img and getattr(img, "filename", "").strip() != ""
        ]

        if len(imagens) > 5:
            raise ValidationError("Pode enviar no máximo 5 imagens.")

        for imagem in imagens:
            nome = imagem.filename.lower()
            if not nome.endswith((".jpg", ".jpeg", ".png", ".webp")):
                raise ValidationError(
                    f"{imagem.filename} não é um tipo de imagem suportado (JPG, PNG, WEBP)."
                )

            imagem.stream.seek(0, os.SEEK_END)
            tamanho = imagem.stream.tell()
            imagem.stream.seek(0)

            if tamanho > 3 * 1024 * 1024:
                raise ValidationError(
                    f"{imagem.filename} excede o tamanho máximo de 3MB."
                )

    def get_dimensoes_string(self):
        a = self.altura_cm.data
        l = self.largura_cm.data
        p = self.profundidade_cm.data
        if a and l and p:
            return f"{a}x{l}x{p} cm"
        return None


# endregion formulario anuncio


# region formulario mensagem
class MensagemForm(FlaskForm):
    assunto = HiddenField()
    conteudo = TextAreaField("Digite uma mensagem:", validators=[DataRequired()])
    submit = SubmitField("Enviar Mensagem")


# endregion formulario mensagem


# region formulario categoria
class CategoriaForm(FlaskForm):
    nome = StringField("Nome da Categoria", validators=[DataRequired()])
    submit = SubmitField("Salvar")

    def validate_categorias(self, field):
        if not field.data:
            raise ValidationError("Selecione pelo menos uma categoria.")


# endregion formulario categoria


# region formulario edita perfil
class EditarPerfilForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    senha = PasswordField("Nova Palavra Passe")
    confirmar_senha = PasswordField("Confirmar Nova Palavra Passe")
    confirmar_senha = PasswordField(
        "Confirmar Nova Palavra Passe",
        validators=[EqualTo("senha", message="As palavras passe não coincidem.")],
    )
    foto = FileField("Foto de Perfil", validators=[Optional()])

    def validate_email(self, field):

        utilizador_existente = Utilizador.query.filter_by(email=field.data).first()

        # Se já existe um utilizador com este email...
        if utilizador_existente:
            # ... e o ID dele não é o do utilizador atualmente em edição (campo oculto ou instância passada)
            if hasattr(self, 'utilizador') and utilizador_existente.id != self.utilizador.id:
                raise ValidationError("Este email já está registado por outro utilizador.")
            elif not hasattr(self, 'utilizador') and utilizador_existente.id != current_user.id:
                raise ValidationError("Este email já está registado por outro utilizador.")



# endregion formulario edita perfil
# region comentario anuncio
class ComentarioForm(FlaskForm):
    conteudo = TextAreaField(
        "Comentário", validators=[DataRequired(), Length(min=1, max=300)]
    )


# endregion comentario anuncio
