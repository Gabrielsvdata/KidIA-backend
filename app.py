from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import config
from middleware.security import (
    register_security_middleware, 
    CSRFProtection,
    ErrorHandler,
    SecureLogger
)
import os

# Inicialização das extensões
jwt = JWTManager()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)


def create_app(config_name=None):
    """Factory function para criar a aplicação Flask"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Configurar CORS com credenciais (para cookies)
    CORS(
        app, 
        origins=app.config['ALLOWED_ORIGINS'], 
        supports_credentials=True,
        methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        allow_headers=['Content-Type', 'Authorization', 'X-CSRF-Token'],
        expose_headers=['X-RateLimit-Limit', 'X-RateLimit-Remaining', 'X-RateLimit-Reset', 'Retry-After']
    )
    
    # Inicializar JWT com suporte a cookies
    jwt.init_app(app)
    
    # Inicializar Rate Limiter
    limiter.init_app(app)
    
    # Registrar middleware de segurança
    register_security_middleware(app)
    
    # Registrar blueprints
    from routes.chat import chat_bp
    from routes.auth import auth_bp
    from routes.health import health_bp
    
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(chat_bp, url_prefix='/chat')
    
    # ==========================================
    # ENDPOINT CSRF TOKEN
    # ==========================================
    @app.route('/csrf-token', methods=['GET'])
    def get_csrf_token():
        """Gera e retorna um token CSRF"""
        token = CSRFProtection.generate_token()
        response = jsonify({"success": True})
        
        is_production = not app.config.get('DEBUG', False)
        # Em produção cross-origin: SameSite=None + Secure=True
        samesite_value = 'None' if is_production else 'Lax'
        
        # Cookie CSRF não é httpOnly para o JS poder ler
        response.set_cookie(
            CSRFProtection.COOKIE_NAME,
            token,
            httponly=False,  # JS precisa ler
            secure=is_production,
            samesite=samesite_value,
            max_age=86400  # 24 horas
        )
        
        return response
    
    # ==========================================
    # ERROR HANDLERS GLOBAIS
    # ==========================================
    @app.errorhandler(429)
    def ratelimit_handler(e):
        """Handler para rate limit excedido"""
        retry_after = int(e.description.split('in')[1].split('second')[0].strip()) if 'in' in str(e.description) else 60
        return ErrorHandler.rate_limit_error(retry_after)
    
    @app.errorhandler(404)
    def not_found_handler(e):
        return ErrorHandler.not_found_error("Endpoint não encontrado")
    
    @app.errorhandler(500)
    def internal_error_handler(e):
        SecureLogger.error("Erro interno do servidor", include_trace=True)
        return ErrorHandler.internal_error(e)
    
    @app.errorhandler(405)
    def method_not_allowed_handler(e):
        return ErrorHandler.validation_error("Método não permitido")
    
    # ==========================================
    # JWT ERROR HANDLERS
    # ==========================================
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "success": False,
            "message": "Token expirado. Faça login novamente."
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            "success": False,
            "message": "Token inválido"
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            "success": False,
            "message": "Token de autenticação não fornecido"
        }), 401
    
    return app


# Instância para Gunicorn (produção)
app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

