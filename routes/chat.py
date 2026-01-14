from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from services.chat_service import chat_service
from functools import wraps
import time

chat_bp = Blueprint('chat', __name__)

# Rate limiting simples (em produção, usar Redis)
_request_counts = {}


def rate_limit(max_requests=10, window=60):
    """Decorator para limitar requisições"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Identificar usuário
            try:
                user_id = get_jwt_identity()
            except:
                user_id = request.remote_addr
            
            current_time = time.time()
            
            # Limpar contagens antigas
            if user_id in _request_counts:
                _request_counts[user_id] = [
                    t for t in _request_counts[user_id] 
                    if current_time - t < window
                ]
            else:
                _request_counts[user_id] = []
            
            # Verificar limite
            if len(_request_counts[user_id]) >= max_requests:
                return jsonify({
                    "success": False,
                    "message": "Muitas mensagens! Espere um pouquinho... ⏰"
                }), 429
            
            # Registrar requisição
            _request_counts[user_id].append(current_time)
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


@chat_bp.route('/message', methods=['POST'])
@jwt_required()
@rate_limit(max_requests=10, window=60)
def send_message():
    """
    Recebe uma mensagem e retorna a resposta do chatbot.
    
    Body:
    {
        "message": "string - pergunta da criança",
        "child_id": "string - ID do perfil da criança",
        "conversation_history": [array opcional de mensagens anteriores]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                "success": False,
                "message": "Por favor, envie uma mensagem"
            }), 400
        
        message = data.get('message', '').strip()
        child_id = data.get('child_id')
        conversation_history = data.get('conversation_history', [])
        
        if not message:
            return jsonify({
                "success": False,
                "message": "A mensagem está vazia"
            }), 400
        
        # Obter resposta do chatbot
        result = chat_service.get_response(message, conversation_history)
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Ops! Algo deu errado. Tente novamente! 🔄",
            "error": str(e)
        }), 500


@chat_bp.route('/quick-message', methods=['POST'])
@rate_limit(max_requests=5, window=60)
def quick_message():
    """
    Endpoint sem autenticação para testes rápidos.
    Limitado a menos requisições.
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                "success": False,
                "message": "Por favor, envie uma mensagem"
            }), 400
        
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({
                "success": False,
                "message": "A mensagem está vazia"
            }), 400
        
        # Obter resposta do chatbot
        result = chat_service.get_response(message)
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Ops! Algo deu errado. Tente novamente! 🔄",
            "error": str(e)
        }), 500


@chat_bp.route('/suggestions', methods=['GET'])
def get_suggestions():
    """Retorna sugestões de perguntas para crianças"""
    suggestions = [
        {"emoji": "🦕", "text": "Por que os dinossauros foram extintos?"},
        {"emoji": "🌙", "text": "Por que a lua muda de forma?"},
        {"emoji": "🌈", "text": "Como o arco-íris se forma?"},
        {"emoji": "🐋", "text": "Qual é o maior animal do mundo?"},
        {"emoji": "⭐", "text": "Por que as estrelas brilham?"},
        {"emoji": "🦋", "text": "Como as lagartas viram borboletas?"},
        {"emoji": "🌋", "text": "O que é um vulcão?"},
        {"emoji": "🐧", "text": "Por que os pinguins não voam?"},
    ]
    
    return jsonify({
        "success": True,
        "suggestions": suggestions
    }), 200
