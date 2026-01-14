from functools import wraps
from flask import request, jsonify, current_app
import time
import re


class SecurityMiddleware:
    """Middleware de segurança para a API KidIA"""
    
    # Padrões de injeção para bloquear
    INJECTION_PATTERNS = [
        r'<script[^>]*>',
        r'javascript:',
        r'on\w+\s*=',
        r'data:text/html',
        r'\{\{.*\}\}',  # Template injection
        r'\$\{.*\}',    # Template literals
    ]
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Remove conteúdo potencialmente perigoso"""
        if not text:
            return text
        
        # Remover tags HTML
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remover caracteres de controle
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        return text.strip()
    
    @staticmethod
    def check_content_type(f):
        """Decorator para verificar Content-Type"""
        @wraps(f)
        def wrapper(*args, **kwargs):
            if request.method in ['POST', 'PUT', 'PATCH']:
                content_type = request.content_type or ''
                if not any(ct in content_type for ct in ['application/json', 'multipart/form-data']):
                    return jsonify({
                        "success": False,
                        "message": "Content-Type inválido"
                    }), 415
            return f(*args, **kwargs)
        return wrapper
    
    @staticmethod
    def validate_request_size(max_size_mb=10):
        """Decorator para limitar tamanho da requisição"""
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                content_length = request.content_length or 0
                max_bytes = max_size_mb * 1024 * 1024
                
                if content_length > max_bytes:
                    return jsonify({
                        "success": False,
                        "message": f"Requisição muito grande. Máximo: {max_size_mb}MB"
                    }), 413
                return f(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def log_request(f):
        """Decorator para logar requisições"""
        @wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Log básico (em produção, usar logging apropriado)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"{request.method} {request.path} - "
                  f"IP: {request.remote_addr}")
            
            response = f(*args, **kwargs)
            
            duration = time.time() - start_time
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"Completed in {duration:.3f}s")
            
            return response
        return wrapper


def add_security_headers(response):
    """Adiciona headers de segurança às respostas"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response


def register_security_middleware(app):
    """Registra middleware de segurança na aplicação"""
    
    @app.after_request
    def apply_security_headers(response):
        return add_security_headers(response)
    
    @app.before_request
    def check_banned_patterns():
        """Verifica padrões perigosos na requisição"""
        if request.data:
            try:
                data = request.data.decode('utf-8', errors='ignore')
                for pattern in SecurityMiddleware.INJECTION_PATTERNS:
                    if re.search(pattern, data, re.IGNORECASE):
                        return jsonify({
                            "success": False,
                            "message": "Requisição bloqueada por segurança"
                        }), 400
            except:
                pass
