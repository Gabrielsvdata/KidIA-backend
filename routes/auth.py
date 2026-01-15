from flask import Blueprint, request, jsonify, current_app, make_response
from flask_jwt_extended import (
    jwt_required, 
    get_jwt_identity, 
    create_access_token,
    create_refresh_token,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
    get_jwt
)
from services.auth_service import auth_service
from middleware.security import (
    InputValidator, 
    ErrorHandler, 
    SecureLogger,
    sanitize_request
)
from app import limiter
import re

auth_bp = Blueprint('auth', __name__)


def validate_email(email: str) -> bool:
    """Valida formato de email"""
    is_valid, _ = InputValidator.validate_email(email)
    return is_valid


def validate_password(password: str) -> tuple[bool, str]:
    """Valida força da senha"""
    return InputValidator.validate_password(password)


def set_auth_cookies(response, access_token: str, refresh_token: str = None):
    """Define cookies de autenticação na resposta"""
    is_production = not current_app.config.get('DEBUG', False)
    
    # Em produção cross-origin: SameSite=None + Secure=True
    # Em desenvolvimento: SameSite=Lax + Secure=False
    samesite_value = 'None' if is_production else 'Lax'
    
    # Access token cookie
    response.set_cookie(
        'access_token',
        access_token,
        httponly=True,
        secure=is_production,
        samesite=samesite_value,
        max_age=900,  # 15 minutos
        path='/'
    )
    
    # Refresh token cookie (apenas se fornecido)
    if refresh_token:
        response.set_cookie(
            'refresh_token',
            refresh_token,
            httponly=True,
            secure=is_production,
            samesite=samesite_value,
            max_age=604800,  # 7 dias
            path='/auth/'  # Apenas para rotas de auth (com barra final)
        )
    
    return response


def clear_auth_cookies(response):
    """Remove cookies de autenticação"""
    response.delete_cookie('access_token', path='/')
    response.delete_cookie('refresh_token', path='/auth/')
    return response


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("3 per minute")
@sanitize_request
def register():
    """
    Registra um novo responsável.
    
    Body:
    {
        "email": "string",
        "password": "string",
        "name": "string"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return ErrorHandler.validation_error("Dados não fornecidos")
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        name = data.get('name', '').strip()
        
        # Validações com mensagens específicas
        if not email or not password or not name:
            return ErrorHandler.validation_error("Email, senha e nome são obrigatórios")
        
        # Validar email
        email_valid, email_error = InputValidator.validate_email(email)
        if not email_valid:
            return ErrorHandler.validation_error(email_error)
        
        # Validar senha
        password_valid, password_error = InputValidator.validate_password(password)
        if not password_valid:
            return ErrorHandler.validation_error(password_error)
        
        # Validar nome
        name_valid, name_error = InputValidator.validate_name(name)
        if not name_valid:
            return ErrorHandler.validation_error(name_error)
        
        # Sanitizar nome
        name = InputValidator.sanitize_string(name, max_length=100)
        
        # Registrar usuário
        result = auth_service.register_parent(email, password, name)
        
        if result['success']:
            SecureLogger.info(f"Novo usuário registrado: {email}")
            return jsonify(result), 201
        else:
            return jsonify(result), 400
        
    except Exception as e:
        SecureLogger.error("Erro ao registrar usuário", include_trace=True)
        return ErrorHandler.internal_error(e)


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """
    Autentica um responsável.
    Tokens são enviados via cookies httpOnly.
    
    Body:
    {
        "email": "string",
        "password": "string"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return ErrorHandler.validation_error("Dados não fornecidos")
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return ErrorHandler.validation_error("Email e senha são obrigatórios")
        
        # Autenticar usuário
        result = auth_service.login(email, password)
        
        if result['success']:
            # Extrair tokens do resultado
            access_token = result.pop('access_token', None)
            refresh_token = result.pop('refresh_token', None)
            
            # Criar resposta com dados do usuário (sem tokens no body)
            response = make_response(jsonify(result))
            
            # Definir cookies httpOnly com os tokens
            if access_token:
                response = set_auth_cookies(response, access_token, refresh_token)
            
            SecureLogger.info(f"Login realizado: {email}")
            return response, 200
        else:
            SecureLogger.warning(f"Tentativa de login falhou: {email}")
            return jsonify(result), 401
        
    except Exception as e:
        SecureLogger.error("Erro ao fazer login", include_trace=True)
        return ErrorHandler.internal_error(e)


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True, locations=['cookies', 'headers'])
@limiter.limit("10 per minute")
def refresh():
    """Renova o token de acesso usando o refresh token do cookie"""
    try:
        identity = get_jwt_identity()
        
        # Criar novo access token
        access_token = create_access_token(identity=identity)
        
        # Criar resposta
        response = make_response(jsonify({
            "success": True,
            "message": "Token renovado"
        }))
        
        # Atualizar cookie do access token
        is_production = not current_app.config.get('DEBUG', False)
        samesite_value = 'None' if is_production else 'Lax'
        
        response.set_cookie(
            'access_token',
            access_token,
            httponly=True,
            secure=is_production,
            samesite=samesite_value,
            max_age=900,
            path='/'
        )
        
        return response, 200
        
    except Exception as e:
        SecureLogger.error("Erro ao renovar token", include_trace=True)
        return ErrorHandler.internal_error(e)


@auth_bp.route('/logout', methods=['POST'])
@jwt_required(optional=True, locations=['cookies', 'headers'])
def logout():
    """
    Faz logout do usuário removendo os cookies de autenticação.
    """
    try:
        response = make_response(jsonify({
            "success": True,
            "message": "Logout realizado com sucesso"
        }))
        
        # Limpar cookies de autenticação
        response = clear_auth_cookies(response)
        
        # Também limpar cookie CSRF
        response.delete_cookie('csrf_token')
        
        SecureLogger.info("Logout realizado")
        return response, 200
        
    except Exception as e:
        SecureLogger.error("Erro ao fazer logout", include_trace=True)
        return ErrorHandler.internal_error(e)


@auth_bp.route('/me', methods=['GET'])
@jwt_required(locations=['cookies', 'headers'])
def get_current_user():
    """Retorna informações do usuário autenticado"""
    try:
        user_id = get_jwt_identity()
        
        # Buscar perfis das crianças
        children_result = auth_service.get_children_profiles(user_id)
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "children": children_result.get('children', [])
        }), 200
        
    except Exception as e:
        SecureLogger.error("Erro ao obter informações do usuário", include_trace=True)
        return ErrorHandler.internal_error(e)


@auth_bp.route('/children', methods=['POST'])
@jwt_required(locations=['cookies', 'headers'])
@sanitize_request
def add_child():
    """
    Adiciona um perfil de criança.
    
    Body:
    {
        "name": "string",
        "age": number (4-12),
        "avatar": "string" (opcional)
    }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return ErrorHandler.validation_error("Dados não fornecidos")
        
        name = data.get('name', '').strip()
        age = data.get('age')
        avatar = data.get('avatar')
        
        if not name or age is None:
            return ErrorHandler.validation_error("Nome e idade são obrigatórios")
        
        # Validar nome
        name_valid, name_error = InputValidator.validate_name(name)
        if not name_valid:
            return ErrorHandler.validation_error(name_error)
        
        # Sanitizar nome
        name = InputValidator.sanitize_string(name, max_length=100)
        
        try:
            age = int(age)
        except:
            return ErrorHandler.validation_error("Idade deve ser um número")
        
        result = auth_service.add_child_profile(user_id, name, age, avatar)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
        
    except Exception as e:
        SecureLogger.error("Erro ao adicionar criança", include_trace=True)
        return ErrorHandler.internal_error(e)


@auth_bp.route('/children', methods=['GET'])
@jwt_required(locations=['cookies', 'headers'])
def get_children():
    """Lista os perfis das crianças do responsável"""
    try:
        user_id = get_jwt_identity()
        result = auth_service.get_children_profiles(user_id)
        
        return jsonify(result), 200
        
    except Exception as e:
        SecureLogger.error("Erro ao listar crianças", include_trace=True)
        return ErrorHandler.internal_error(e)


@auth_bp.route('/children/<child_id>', methods=['GET'])
@jwt_required(locations=['cookies', 'headers'])
def get_child(child_id):
    """Obtém perfil de uma criança específica"""
    try:
        user_id = get_jwt_identity()
        
        # Sanitizar child_id
        child_id = InputValidator.sanitize_string(child_id, max_length=36)
        
        result = auth_service.get_child_profile(child_id, user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return ErrorHandler.not_found_error("Perfil não encontrado")
        
    except Exception as e:
        SecureLogger.error("Erro ao obter perfil", include_trace=True)
        return ErrorHandler.internal_error(e)
