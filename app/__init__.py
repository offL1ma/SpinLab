from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash
from datetime import timedelta, datetime, UTC
import secrets
import os
from config import Config
from apscheduler.schedulers.background import BackgroundScheduler
from flask_wtf import CSRFProtect

# Inicializações globais

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Precisa de iniciar sessão para aceder a esta página."
login_manager.login_message_category = "erro"
migrate = Migrate()
csrf = CSRFProtect()


# region limpeza de anúncios antigos
def limpar_anuncios_antigos():
    from .models import Anuncio

    prazo = datetime.now(UTC) - timedelta(days=7)
    antigos = (
        Anuncio.query.filter_by(eliminado=True)
        .filter(Anuncio.data_criacao < prazo)
        .all()
    )
    for anuncio in antigos:
        db.session.delete(anuncio)
    db.session.commit()


# endregion limpeza de anúncios antigos


# region criação da app Flask
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.permanent_session_lifetime = timedelta(minutes=30)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    migrate.init_app(app, db)
    csrf.init_app(app)
    app.config["WTF_CSRF_ENABLED"] = False

    @app.after_request
    def add_header(response):
        if "text/css" in response.content_type or "image/" in response.content_type:
            response.cache_control.max_age = 604800  # 7 dias
        return response

    with app.app_context():
        from .models import Categoria, Utilizador
        try:
            # Criar categorias predefinidas
            categorias = current_app.config.get(
                "CATEGORIAS_PREDEFINIDAS",
                [
                    "pop|rock",
                    "folk|country",
                    "indie|alternativa",
                    "jazz|blues",
                    "clássica|ópera",
                    "hiphop|rap",
                    "eletrónica|dance",
                    "punk|hardcore",
                    "Portuguesa",
                    "Brasileira",
                ],
            )
            for nome in categorias:
                if not Categoria.query.filter_by(nome=nome).first():
                    db.session.add(Categoria(nome=nome))

            # Criar admin padrão se não existir
            if not Utilizador.query.filter_by(papel="admin").first():
                admin = Utilizador(nome="Admin", email="admin@spinlab.com", papel="admin")
                admin.definir_senha("admin")
                db.session.add(admin)

            db.session.commit()

        except Exception as e:
            print("⚠️ Base ainda não pronta, a criação de dados foi ignorada temporariamente.")
            print(e)

    @app.context_processor
    def inject_categorias():
        from .models import Categoria

        return dict(categorias=Categoria.query.all())

    # Registrar os blueprints
    from .routes import auth, anuncios, admin, mensagens, utilizadores

    app.register_blueprint(auth.bp)
    app.register_blueprint(anuncios.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(mensagens.bp)
    app.register_blueprint(utilizadores.bp)

    # Scheduler para eliminar anúncios antigos automaticamente
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=limpar_anuncios_antigos, trigger="interval", days=1)
    scheduler.start()
    @app.route("/criar-admin")
    def criar_admin():
        from .models import Utilizador
        if not Utilizador.query.filter_by(papel="admin").first():
            admin = Utilizador(nome="Admin", email="admin@spinlab.com", papel="admin")
            admin.definir_senha("admin")  # Palavra-passe: admin
            db.session.add(admin)
            db.session.commit()
            return "Admin criado com sucesso!"
        return "Admin já existe."
    
    @app.route("/init-db")
    def init_db():
        with app.app_context():
            db.create_all()
        return "Tabelas criadas com sucesso."
        

    return app
    # endregion criação da app Flask
