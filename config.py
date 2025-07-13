import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "chave-secreta"
    
    # Usa PostgreSQL da Supabase, com fallback para SQLite local
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///spinlab.db")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join("app", "static", "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

    CATEGORIAS_PREDEFINIDAS = [
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
        "Outras",
    ]
