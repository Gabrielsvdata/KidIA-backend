import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configurações base da aplicação"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-dev-secret')
    
    # JWT com cookies httpOnly
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_TOKEN_LOCATION = ['cookies', 'headers']  # Cookies primeiro, headers como fallback
    JWT_COOKIE_SECURE = False  # Será True em produção (HTTPS)
    JWT_COOKIE_CSRF_PROTECT = False  # Usamos nossa própria proteção CSRF
    JWT_COOKIE_SAMESITE = 'Lax'  # Lax para desenvolvimento
    JWT_ACCESS_COOKIE_NAME = 'access_token'
    JWT_REFRESH_COOKIE_NAME = 'refresh_token'
    JWT_ACCESS_COOKIE_PATH = '/'
    JWT_REFRESH_COOKIE_PATH = '/auth/'
    
    # CSRF
    CSRF_COOKIE_NAME = 'csrf_token'
    CSRF_HEADER_NAME = 'X-CSRF-Token'
    
    # Groq API (gratuito e rápido)
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    # CORS - Domínios permitidos
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
    
    # Rate Limiting
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_DEFAULT = "200 per day, 50 per hour"
    RATELIMIT_HEADERS_ENABLED = True
    
    # Limites de segurança
    MAX_MESSAGE_LENGTH = 2000
    MAX_NAME_LENGTH = 100
    MAX_EMAIL_LENGTH = 255
    MAX_PASSWORD_LENGTH = 128
    MAX_REQUESTS_PER_MINUTE = 10
    
    # Configurações do chatbot infantil
    CHILD_FRIENDLY_MODE = True
    MIN_AGE = 4
    MAX_AGE = 12


class DevelopmentConfig(Config):
    """Configurações de desenvolvimento"""
    DEBUG = True
    JWT_COOKIE_SECURE = False  # Permite HTTP em dev
    JWT_COOKIE_SAMESITE = 'Lax'
    

class ProductionConfig(Config):
    """Configurações de produção"""
    DEBUG = False
    JWT_COOKIE_SECURE = True  # Apenas HTTPS
    JWT_COOKIE_SAMESITE = 'None'  # Necessário para cross-origin (frontend Vercel, backend Render)
    RATELIMIT_STORAGE_URI = os.getenv('REDIS_URL', "memory://")
    

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
