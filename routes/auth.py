from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    jwt_required, 
    get_jwt_identity, 
    create_access_token
)
from services.auth_service import auth_service
import re

auth_bp = Blueprint('auth', __name__)


def validate_email(email: str) -> bool:
    """Valida formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password: str) -> tuple[bool, str]:
    """Valida força da senha"""
    if len(password) < 8:
        return False, "Senha deve ter no mínimo 8 caracteres"
    if not re.search(r'[A-Z]', password):
        return False, "Senha deve ter pelo menos uma letra maiúscula"
    if not re.search(r'[a-z]', password):
        return False, "Senha deve ter pelo menos uma letra minúscula"
    if not re.search(r'\d', password):
        return False, "Senha deve ter pelo menos um número"
    return True, ""


@auth_bp.route('/register', methods=['POST'])
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
            return jsonify({
                "success": False,
                "message": "Dados não fornecidos"
            }), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        name = data.get('name', '').strip()
        
        # Validações
        if not email or not password or not name:
            return jsonify({
                "success": False,
                "message": "Email, senha e nome são obrigatórios"
            }), 400
        
        if not validate_email(email):
            return jsonify({
                "success": False,
                "message": "Email inválido"
            }), 400
        
        is_valid_password, password_error = validate_password(password)
        if not is_valid_password:
            return jsonify({
                "success": False,
                "message": password_error
            }), 400
        
        # Registrar usuário
        result = auth_service.register_parent(email, password, name)
        
        return jsonify(result), 201 if result['success'] else 400
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Erro ao registrar",
            "error": str(e)
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Autentica um responsável.
    
    Body:
    {
        "email": "string",
        "password": "string"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "message": "Dados não fornecidos"
            }), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({
                "success": False,
                "message": "Email e senha são obrigatórios"
            }), 400
        
        result = auth_service.login(email, password)
        
        return jsonify(result), 200 if result['success'] else 401
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Erro ao fazer login",
            "error": str(e)
        }), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Renova o token de acesso usando o refresh token"""
    try:
        identity = get_jwt_identity()
        access_token = create_access_token(identity=identity)
        
        return jsonify({
            "success": True,
            "access_token": access_token
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Erro ao renovar token",
            "error": str(e)
        }), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
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
        return jsonify({
            "success": False,
            "message": "Erro ao obter informações",
            "error": str(e)
        }), 500


@auth_bp.route('/children', methods=['POST'])
@jwt_required()
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
            return jsonify({
                "success": False,
                "message": "Dados não fornecidos"
            }), 400
        
        name = data.get('name', '').strip()
        age = data.get('age')
        avatar = data.get('avatar')
        
        if not name or age is None:
            return jsonify({
                "success": False,
                "message": "Nome e idade são obrigatórios"
            }), 400
        
        try:
            age = int(age)
        except:
            return jsonify({
                "success": False,
                "message": "Idade deve ser um número"
            }), 400
        
        result = auth_service.add_child_profile(user_id, name, age, avatar)
        
        return jsonify(result), 201 if result['success'] else 400
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Erro ao adicionar criança",
            "error": str(e)
        }), 500


@auth_bp.route('/children', methods=['GET'])
@jwt_required()
def get_children():
    """Lista os perfis das crianças do responsável"""
    try:
        user_id = get_jwt_identity()
        result = auth_service.get_children_profiles(user_id)
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Erro ao listar crianças",
            "error": str(e)
        }), 500


@auth_bp.route('/children/<child_id>', methods=['GET'])
@jwt_required()
def get_child(child_id):
    """Obtém perfil de uma criança específica"""
    try:
        user_id = get_jwt_identity()
        result = auth_service.get_child_profile(child_id, user_id)
        
        return jsonify(result), 200 if result['success'] else 404
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Erro ao obter perfil",
            "error": str(e)
        }), 500
