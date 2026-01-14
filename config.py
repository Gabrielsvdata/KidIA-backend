import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configurações base da aplicação"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-dev-secret')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Groq API (gratuito e rápido)
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    # CORS
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
    
    # Limites de segurança para crianças
    MAX_MESSAGE_LENGTH = 500
    MAX_REQUESTS_PER_MINUTE = 10
    
    # Configurações do chatbot infantil
    CHILD_FRIENDLY_MODE = True
    MIN_AGE = 4
    MAX_AGE = 12


class DevelopmentConfig(Config):
    """Configurações de desenvolvimento"""
    DEBUG = True
    

class ProductionConfig(Config):
    """Configurações de produção"""
    DEBUG = False
    

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
