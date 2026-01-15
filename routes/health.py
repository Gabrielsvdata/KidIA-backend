from flask import Blueprint, jsonify, Response
import time

health_bp = Blueprint('health', __name__)

# Cache do health check para reduzir processamento
_health_cache = {'response': None, 'timestamp': 0}
_HEALTH_CACHE_TTL = 5  # 5 segundos


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check otimizado para Render.
    - Resposta mínima e rápida
    - Cache de 5 segundos
    - Sem verificação de banco (mais rápido)
    """
    current_time = time.time()
    
    # Retornar cache se ainda válido
    if _health_cache['response'] and (current_time - _health_cache['timestamp']) < _HEALTH_CACHE_TTL:
        return _health_cache['response']
    
    # Resposta mínima para health check rápido
    response = Response(
        '{"status":"ok"}',
        status=200,
        mimetype='application/json'
    )
    response.headers['Cache-Control'] = 'no-cache'
    
    # Atualizar cache
    _health_cache['response'] = response
    _health_cache['timestamp'] = current_time
    
    return response


@health_bp.route('/health/detailed', methods=['GET'])
def health_check_detailed():
    """Health check detalhado (mais lento, usar apenas para debug)"""
    return jsonify({
        "status": "healthy",
        "service": "Kiko Backend",
        "version": "1.0.0"
    }), 200


@health_bp.route('/', methods=['GET'])
def index():
    """Rota inicial da API"""
    return jsonify({
        "message": "Bem-vindo à API do Kiko! 🌟",
        "description": "Chatbot educativo para crianças",
        "endpoints": {
            "health": "/api/health",
            "auth": "/api/auth",
            "chat": "/api/chat",
            "voice": "/api/voice"
        }
    }), 200
