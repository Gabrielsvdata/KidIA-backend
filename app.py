from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import config
import os

# Inicialização das extensões
jwt = JWTManager()


def create_app(config_name=None):
    """Factory function para criar a aplicação Flask"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Configurar CORS
    CORS(app, origins=app.config['ALLOWED_ORIGINS'], supports_credentials=True, 
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         allow_headers=['Content-Type', 'Authorization'])
    
    # Inicializar JWT
    jwt.init_app(app)
    
    # Registrar blueprints
    from routes.chat import chat_bp
    from routes.auth import auth_bp
    from routes.health import health_bp
    
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(chat_bp, url_prefix='/chat')
    
    return app


# Instância para Gunicorn (produção)
app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
