from flask import Blueprint, jsonify

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """Verifica se a API está funcionando"""
    return jsonify({
        "status": "healthy",
        "service": "KidIA Backend",
        "version": "1.0.0"
    }), 200


@health_bp.route('/', methods=['GET'])
def index():
    """Rota inicial da API"""
    return jsonify({
        "message": "Bem-vindo à API do KidIA! 🌟",
        "description": "Chatbot educativo para crianças",
        "endpoints": {
            "health": "/api/health",
            "auth": "/api/auth",
            "chat": "/api/chat",
            "voice": "/api/voice"
        }
    }), 200
