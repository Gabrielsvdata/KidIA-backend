"""
Middleware de Segurança Completo para KidIA
===========================================
Inclui: CSRF, Rate Limiting, Headers de Segurança, Sanitização, Logging Seguro
"""

from functools import wraps
from flask import request, jsonify, current_app, g
import time
import re
import secrets
import logging
from typing import Callable, Any

# Tentar importar bleach, fallback se não disponível
try:
    import bleach
    HAS_BLEACH = True
except ImportError:
    HAS_BLEACH = False

# Configuração de logging seguro
logger = logging.getLogger('kidia.security')


class SecureLogger:
    """Logger que oculta automaticamente dados sensíveis"""
    
    SENSITIVE_FIELDS = [
        'password', 'senha', 'token', 'access_token', 'refresh_token',
        'secret', 'authorization', 'api_key', 'apikey', 'jwt', 'csrf'
    ]
    
    @classmethod
    def mask_sensitive_data(cls, data: Any) -> Any:
        """Mascara dados sensíveis em dicionários e strings"""
        if isinstance(data, dict):
            masked = {}
            for key, value in data.items():
                key_lower = key.lower()
                if any(field in key_lower for field in cls.SENSITIVE_FIELDS):
                    masked[key] = '***REDACTED***'
                else:
                    masked[key] = cls.mask_sensitive_data(value)
            return masked
        elif isinstance(data, list):
            return [cls.mask_sensitive_data(item) for item in data]
        elif isinstance(data, str):
            result = data
            for field in cls.SENSITIVE_FIELDS:
                pattern = rf'({field}["\s:=]+)[^\s,}}"\']+' 
                result = re.sub(pattern, r'\1***REDACTED***', result, flags=re.IGNORECASE)
            return result
        return data
    
    @classmethod
    def info(cls, message: str, data: Any = None):
        masked = cls.mask_sensitive_data(data) if data else None
        logger.info(f"{message} {masked if masked else ''}")
    
    @classmethod
    def warning(cls, message: str, data: Any = None):
        masked = cls.mask_sensitive_data(data) if data else None
        logger.warning(f"{message} {masked if masked else ''}")
    
    @classmethod
    def error(cls, message: str, data: Any = None, include_trace: bool = False):
        masked = cls.mask_sensitive_data(data) if data else None
        try:
            debug_mode = current_app.config.get('DEBUG', False)
        except RuntimeError:
            debug_mode = False
        
        if include_trace and not debug_mode:
            logger.error(f"{message} {masked if masked else ''}")
        else:
            logger.error(f"{message} {masked if masked else ''}", exc_info=include_trace)


class CSRFProtection:
    """Sistema de proteção CSRF"""
    
    TOKEN_LENGTH = 64
    COOKIE_NAME = 'csrf_token'
    HEADER_NAME = 'X-CSRF-Token'
    
    @classmethod
    def generate_token(cls) -> str:
        """Gera um token CSRF seguro"""
        return secrets.token_hex(cls.TOKEN_LENGTH // 2)
    
    @classmethod
    def get_token_from_request(cls) -> tuple:
        """Obtém token do header e do cookie"""
        header_token = request.headers.get(cls.HEADER_NAME)
        cookie_token = request.cookies.get(cls.COOKIE_NAME)
        return header_token, cookie_token
    
    @classmethod
    def validate_token(cls) -> tuple:
        """Valida se o token CSRF do header corresponde ao do cookie."""
        header_token, cookie_token = cls.get_token_from_request()
        
        if not cookie_token:
            return False, "Token CSRF não encontrado"
        
        if not header_token:
            return False, "Token CSRF inválido"
        
        if not secrets.compare_digest(header_token, cookie_token):
            return False, "Token CSRF inválido"
        
        return True, ""
    
    @classmethod
    def validate_origin(cls) -> tuple:
        """Valida Origin e Referer headers"""
        try:
            allowed_origins = current_app.config.get('ALLOWED_ORIGINS', [])
            debug_mode = current_app.config.get('DEBUG', False)
        except RuntimeError:
            return True, ""
        
        origin = request.headers.get('Origin')
        referer = request.headers.get('Referer')
        
        if not origin and not referer:
            if debug_mode:
                return True, ""
            return False, "Origem da requisição não identificada"
        
        if origin:
            origin_valid = any(
                origin == allowed or origin.startswith(allowed.rstrip('/'))
                for allowed in allowed_origins
            )
            if not origin_valid:
                SecureLogger.warning(f"Origem bloqueada: {origin}")
                return False, "Origem não autorizada"
        
        if referer and not origin:
            referer_valid = any(
                referer.startswith(allowed.rstrip('/'))
                for allowed in allowed_origins
            )
            if not referer_valid:
                SecureLogger.warning(f"Referer bloqueado: {referer}")
                return False, "Origem não autorizada"
        
        return True, ""


class InputValidator:
    """Validação e sanitização de inputs"""
    
    INJECTION_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'data:text/html',
        r'\{\{.*\}\}',
        r'\$\{.*\}',
        r'eval\s*\(',
        r'exec\s*\(',
    ]
    
    ALLOWED_TAGS: list = []
    ALLOWED_ATTRIBUTES: dict = {}
    
    @classmethod
    def sanitize_string(cls, text: str, max_length: int = 500) -> str:
        """Sanitiza uma string removendo conteúdo perigoso"""
        if not text:
            return ""
        
        text = str(text)[:max_length]
        
        if HAS_BLEACH:
            text = bleach.clean(
                text,
                tags=cls.ALLOWED_TAGS,
                attributes=cls.ALLOWED_ATTRIBUTES,
                strip=True
            )
        else:
            text = re.sub(r'<[^>]+>', '', text)
        
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        for pattern in cls.INJECTION_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        return text.strip()
    
    @classmethod
    def validate_email(cls, email: str) -> tuple:
        """Valida formato de email com regex robusto"""
        if not email:
            return False, "Email é obrigatório"
        
        try:
            max_length = current_app.config.get('MAX_EMAIL_LENGTH', 255)
        except RuntimeError:
            max_length = 255
            
        if len(email) > max_length:
            return False, f"Email deve ter no máximo {max_length} caracteres"
        
        pattern = r'^[a-zA-Z0-9](?:[a-zA-Z0-9._%+-]{0,62}[a-zA-Z0-9])?@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z]{2,})+$'
        
        if not re.match(pattern, email):
            return False, "Email inválido"
        
        return True, ""
    
    @classmethod
    def validate_password(cls, password: str) -> tuple:
        """Valida força da senha"""
        if not password:
            return False, "Senha é obrigatória"
        
        try:
            max_length = current_app.config.get('MAX_PASSWORD_LENGTH', 128)
        except RuntimeError:
            max_length = 128
            
        if len(password) > max_length:
            return False, f"Senha deve ter no máximo {max_length} caracteres"
        
        if len(password) < 8:
            return False, "Senha deve ter no mínimo 8 caracteres"
        
        if not re.search(r'[A-Z]', password):
            return False, "Senha deve ter pelo menos uma letra maiúscula"
        
        if not re.search(r'[a-z]', password):
            return False, "Senha deve ter pelo menos uma letra minúscula"
        
        if not re.search(r'\d', password):
            return False, "Senha deve ter pelo menos um número"
        
        return True, ""
    
    @classmethod
    def validate_name(cls, name: str) -> tuple:
        """Valida nome"""
        if not name:
            return False, "Nome é obrigatório"
        
        try:
            max_length = current_app.config.get('MAX_NAME_LENGTH', 100)
        except RuntimeError:
            max_length = 100
            
        if len(name) > max_length:
            return False, f"Nome deve ter no máximo {max_length} caracteres"
        
        if not re.match(r'^[a-zA-ZÀ-ÿ\s\'-]+$', name):
            return False, "Nome contém caracteres inválidos"
        
        return True, ""
    
    @classmethod
    def validate_message(cls, message: str) -> tuple:
        """Valida mensagem do chat"""
        if not message:
            return False, "Mensagem é obrigatória"
        
        try:
            max_length = current_app.config.get('MAX_MESSAGE_LENGTH', 2000)
        except RuntimeError:
            max_length = 2000
            
        if len(message) > max_length:
            return False, f"Mensagem deve ter no máximo {max_length} caracteres"
        
        return True, ""


class SecurityHeaders:
    """Adiciona headers de segurança nas respostas"""
    
    @staticmethod
    def add_security_headers(response):
        """Adiciona headers de segurança à resposta"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; frame-ancestors 'none'"
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        try:
            debug_mode = current_app.config.get('DEBUG', False)
        except RuntimeError:
            debug_mode = False
            
        if not debug_mode:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response


class ErrorHandler:
    """Tratamento padronizado de erros"""
    
    @staticmethod
    def handle_error(message: str, status_code: int = 500, error: Exception = None) -> tuple:
        """Retorna resposta de erro padronizada"""
        response_data = {
            "success": False,
            "message": message
        }
        
        try:
            debug_mode = current_app.config.get('DEBUG', False)
        except RuntimeError:
            debug_mode = False
        
        if debug_mode and error:
            response_data["error"] = str(error)
        
        if error:
            SecureLogger.error(message, {"status_code": status_code}, include_trace=True)
        
        return jsonify(response_data), status_code
    
    @staticmethod
    def validation_error(message: str) -> tuple:
        return ErrorHandler.handle_error(message, 400)
    
    @staticmethod
    def unauthorized_error(message: str = "Não autorizado") -> tuple:
        return ErrorHandler.handle_error(message, 401)
    
    @staticmethod
    def forbidden_error(message: str = "Acesso negado") -> tuple:
        return ErrorHandler.handle_error(message, 403)
    
    @staticmethod
    def not_found_error(message: str = "Recurso não encontrado") -> tuple:
        return ErrorHandler.handle_error(message, 404)
    
    @staticmethod
    def rate_limit_error(retry_after: int = 60) -> tuple:
        message = f"Muitas tentativas. Aguarde {retry_after} segundos"
        response = jsonify({
            "success": False,
            "message": message,
            "retry_after": retry_after
        })
        response.headers['Retry-After'] = str(retry_after)
        return response, 429
    
    @staticmethod
    def internal_error(error: Exception = None) -> tuple:
        try:
            debug_mode = current_app.config.get('DEBUG', False)
        except RuntimeError:
            debug_mode = False
        message = "Erro interno do servidor" if not debug_mode else str(error)
        return ErrorHandler.handle_error(message, 500, error)


# ==========================================
# DECORATORS DE SEGURANÇA
# ==========================================

def csrf_protect(f: Callable) -> Callable:
    """Decorator para proteção CSRF em rotas POST/PUT/DELETE"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            origin_valid, origin_error = CSRFProtection.validate_origin()
            if not origin_valid:
                return ErrorHandler.forbidden_error(origin_error)
            
            csrf_valid, csrf_error = CSRFProtection.validate_token()
            if not csrf_valid:
                return ErrorHandler.forbidden_error(csrf_error)
        
        return f(*args, **kwargs)
    return wrapper


def csrf_protect_with_bypass(exempt_endpoints: list = None) -> Callable:
    """Decorator CSRF com bypass para endpoints específicos (login, etc)"""
    if exempt_endpoints is None:
        exempt_endpoints = []
    
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            if request.endpoint in exempt_endpoints:
                return f(*args, **kwargs)
            
            if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
                origin_valid, origin_error = CSRFProtection.validate_origin()
                if not origin_valid:
                    return ErrorHandler.forbidden_error(origin_error)
                
                csrf_valid, csrf_error = CSRFProtection.validate_token()
                if not csrf_valid:
                    return ErrorHandler.forbidden_error(csrf_error)
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


def validate_json(f: Callable) -> Callable:
    """Decorator para validar que a requisição tem JSON válido"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.content_type or ''
            if 'application/json' not in content_type:
                return ErrorHandler.validation_error("Content-Type deve ser application/json")
            
            try:
                data = request.get_json()
                if data is None:
                    return ErrorHandler.validation_error("Dados JSON inválidos")
            except Exception:
                return ErrorHandler.validation_error("Dados JSON inválidos")
        
        return f(*args, **kwargs)
    return wrapper


def sanitize_request(f: Callable) -> Callable:
    """Decorator para sanitizar todos os inputs da requisição"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                data = request.get_json()
                if data and isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, str):
                            if 'password' not in key.lower():
                                data[key] = InputValidator.sanitize_string(value)
                    g.sanitized_data = data
            except Exception:
                pass
        
        return f(*args, **kwargs)
    return wrapper


# ==========================================
# FUNÇÃO PARA REGISTRAR MIDDLEWARE
# ==========================================

def register_security_middleware(app):
    """Registra middleware de segurança na aplicação"""
    
    @app.after_request
    def apply_security_headers(response):
        return SecurityHeaders.add_security_headers(response)
    
    @app.before_request
    def check_banned_patterns():
        """Verifica padrões perigosos na requisição"""
        if request.data:
            try:
                data = request.data.decode('utf-8', errors='ignore')
                for pattern in InputValidator.INJECTION_PATTERNS:
                    if re.search(pattern, data, re.IGNORECASE):
                        return jsonify({
                            "success": False,
                            "message": "Requisição bloqueada por segurança"
                        }), 400
            except:
                pass


# ==========================================
# INSTÂNCIAS GLOBAIS
# ==========================================

secure_logger = SecureLogger()
csrf_protection = CSRFProtection()
input_validator = InputValidator()
security_headers = SecurityHeaders()
error_handler = ErrorHandler()

