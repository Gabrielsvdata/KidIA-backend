from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from services.chat_service import chat_service
from services.memory_service import memory_service
from middleware.security import InputValidator, ErrorHandler, SecureLogger, sanitize_request
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
            remaining_time = int(window - (current_time - _request_counts[user_id][0])) if _request_counts[user_id] else window
            
            if len(_request_counts[user_id]) >= max_requests:
                return ErrorHandler.rate_limit_error(remaining_time)
            
            # Registrar requisição
            _request_counts[user_id].append(current_time)
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


@chat_bp.route('/message', methods=['POST'])
@jwt_required(locations=['cookies', 'headers'])
@rate_limit(max_requests=10, window=60)
@sanitize_request
def send_message():
    """
    Recebe uma mensagem e retorna a resposta do chatbot.
    Agora com memória persistente!
    
    Body:
    {
        "message": "string - pergunta da criança",
        "child_id": "string - ID do perfil da criança (OBRIGATÓRIO para memória)",
        "conversation_history": [array opcional - fallback se não usar child_id]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return ErrorHandler.validation_error("Por favor, envie uma mensagem")
        
        message = data.get('message', '').strip()
        child_id = data.get('child_id')
        conversation_history = data.get('conversation_history', [])
        
        # Validar mensagem
        msg_valid, msg_error = InputValidator.validate_message(message)
        if not msg_valid:
            return ErrorHandler.validation_error(msg_error)
        
        # Sanitizar mensagem
        message = InputValidator.sanitize_string(message, max_length=2000)
        
        if not message:
            return ErrorHandler.validation_error("A mensagem está vazia")
        
        # Obter resposta do chatbot (com memória se child_id fornecido)
        result = chat_service.get_response(message, child_id, conversation_history)
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        SecureLogger.error("Erro no chat", include_trace=True)
        return ErrorHandler.internal_error(e)


@chat_bp.route('/quick-message', methods=['POST'])
@rate_limit(max_requests=5, window=60)
@sanitize_request
def quick_message():
    """
    Endpoint sem autenticação para testes rápidos.
    Limitado a menos requisições.
    Agora com suporte a histórico de conversa!
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return ErrorHandler.validation_error("Por favor, envie uma mensagem")
        
        message = data.get('message', '').strip()
        conversation_history = data.get('conversation_history', [])
        
        # Validar e sanitizar
        msg_valid, msg_error = InputValidator.validate_message(message)
        if not msg_valid:
            return ErrorHandler.validation_error(msg_error)
        
        message = InputValidator.sanitize_string(message, max_length=2000)
        
        if not message:
            return ErrorHandler.validation_error("A mensagem está vazia")
        
        # Obter resposta do chatbot (agora com histórico)
        result = chat_service.get_response(message, None, conversation_history)
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        SecureLogger.error("Erro no quick-message", include_trace=True)
        return ErrorHandler.internal_error(e)


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


# =====================================================
# ROTAS DE ALERTAS PARA OS PAIS
# =====================================================

@chat_bp.route('/alerts', methods=['GET'])
@jwt_required(locations=['cookies', 'headers'])
def get_alerts():
    """
    Retorna os alertas de perguntas sensíveis para os pais.
    
    Query params:
    - unread_only: bool (default: false) - retornar apenas não lidos
    - limit: int (default: 50) - limite de alertas
    """
    try:
        parent_id = get_jwt_identity()
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        limit = min(int(request.args.get('limit', 50)), 100)
        
        if unread_only:
            alerts = memory_service.get_unread_alerts(parent_id)
        else:
            alerts = memory_service.get_all_alerts(parent_id, limit)
        
        # Formatar datas para JSON
        for alert in alerts:
            if alert.get('created_at'):
                alert['created_at'] = alert['created_at'].isoformat()
            if alert.get('read_at'):
                alert['read_at'] = alert['read_at'].isoformat()
        
        return jsonify({
            "success": True,
            "alerts": alerts,
            "count": len(alerts),
            "unread_count": len([a for a in alerts if not a.get('was_read')])
        }), 200
        
    except Exception as e:
        SecureLogger.error("Erro ao buscar alertas", include_trace=True)
        return ErrorHandler.internal_error(e)


@chat_bp.route('/alerts/<alert_id>/read', methods=['POST'])
@jwt_required(locations=['cookies', 'headers'])
def mark_alert_read(alert_id):
    """Marca um alerta específico como lido"""
    try:
        parent_id = get_jwt_identity()
        
        # Sanitizar alert_id
        alert_id = InputValidator.sanitize_string(alert_id, max_length=36)
        
        success = memory_service.mark_alert_as_read(alert_id, parent_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Alerta marcado como lido"
            }), 200
        else:
            return ErrorHandler.not_found_error("Alerta não encontrado")
            
    except Exception as e:
        SecureLogger.error("Erro ao marcar alerta", include_trace=True)
        return ErrorHandler.internal_error(e)


@chat_bp.route('/alerts/read-all', methods=['POST'])
@jwt_required(locations=['cookies', 'headers'])
def mark_all_alerts_read():
    """Marca todos os alertas como lidos"""
    try:
        parent_id = get_jwt_identity()
        count = memory_service.mark_all_alerts_as_read(parent_id)
        
        return jsonify({
            "success": True,
            "message": f"{count} alertas marcados como lidos"
        }), 200
        
    except Exception as e:
        SecureLogger.error("Erro ao marcar alertas", include_trace=True)
        return ErrorHandler.internal_error(e)


# =====================================================
# ROTAS DE MEMÓRIA/CONTEXTO DA CRIANÇA
# =====================================================

@chat_bp.route('/child/<child_id>/memory', methods=['GET'])
@jwt_required(locations=['cookies', 'headers'])
def get_child_memory(child_id):
    """
    Retorna o contexto de memória de uma criança.
    (O que o Kiko lembra sobre ela)
    """
    try:
        # Sanitizar child_id
        child_id = InputValidator.sanitize_string(child_id, max_length=36)
        
        context = memory_service.get_memory_context(child_id)
        
        return jsonify({
            "success": True,
            "memory_context": context
        }), 200
        
    except Exception as e:
        SecureLogger.error("Erro ao buscar memória", include_trace=True)
        return ErrorHandler.internal_error(e)


@chat_bp.route('/child/<child_id>/memory', methods=['PUT'])
@jwt_required(locations=['cookies', 'headers'])
@sanitize_request
def update_child_memory(child_id):
    """
    Permite aos pais atualizar/corrigir informações da memória.
    
    Body:
    {
        "nome": "string",
        "cor_favorita": "string",
        "animal_favorito": "string",
        "interesses": ["string", ...]
    }
    """
    try:
        # Sanitizar child_id
        child_id = InputValidator.sanitize_string(child_id, max_length=36)
        
        data = request.get_json()
        
        if not data:
            return ErrorHandler.validation_error("Dados não fornecidos")
        
        # Sanitizar dados de entrada
        sanitized_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized_data[key] = InputValidator.sanitize_string(value, max_length=200)
            elif isinstance(value, list):
                sanitized_data[key] = [
                    InputValidator.sanitize_string(str(v), max_length=100) 
                    for v in value[:10]  # Limitar a 10 items
                ]
            else:
                sanitized_data[key] = value
        
        updated_context = memory_service.update_memory_context(child_id, sanitized_data)
        
        return jsonify({
            "success": True,
            "message": "Memória atualizada",
            "memory_context": updated_context
        }), 200
        
    except Exception as e:
        SecureLogger.error("Erro ao atualizar memória", include_trace=True)
        return ErrorHandler.internal_error(e)


@chat_bp.route('/child/<child_id>/end-session', methods=['POST'])
@jwt_required(locations=['cookies', 'headers'])
def end_chat_session(child_id):
    """Encerra a sessão de conversa atual da criança"""
    try:
        # Sanitizar child_id
        child_id = InputValidator.sanitize_string(child_id, max_length=36)
        
        session_id = memory_service.get_or_create_session(child_id)
        memory_service.end_session(session_id)
        
        return jsonify({
            "success": True,
            "message": "Sessão encerrada"
        }), 200
        
    except Exception as e:
        SecureLogger.error("Erro ao encerrar sessão", include_trace=True)
        return ErrorHandler.internal_error(e)
