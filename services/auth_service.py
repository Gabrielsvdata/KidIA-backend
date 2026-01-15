from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token
from datetime import datetime
import uuid

# Importação condicional do banco de dados
try:
    from database.connection import Database
    USE_DATABASE = True
except:
    USE_DATABASE = False


class AuthService:
    """Serviço de autenticação para o KidIA"""
    
    # Banco de dados em memória (fallback se MySQL não estiver disponível)
    _users = {}
    _children_profiles = {}
    
    def _use_db(self):
        """Verifica se deve usar o banco de dados"""
        if not USE_DATABASE:
            return False
        try:
            ok, _ = Database.test_connection()
            return ok
        except:
            return False
    
    # ==================== REGISTRO ====================
    
    def register_parent(self, email: str, password: str, name: str) -> dict:
        """Registra um novo responsável"""
        try:
            if self._use_db():
                return self._register_parent_db(email, password, name)
            else:
                return self._register_parent_memory(email, password, name)
        except Exception as e:
            return {
                "success": False,
                "message": "Erro ao criar conta",
                "error": str(e)
            }
    
    def _register_parent_db(self, email: str, password: str, name: str) -> dict:
        """Registra no banco de dados MySQL"""
        # Verificar se email já existe
        existing = Database.execute_query(
            "SELECT id FROM parents WHERE email = %s",
            (email,),
            fetch='one'
        )
        
        if existing:
            return {
                "success": False,
                "message": "Este email já está cadastrado"
            }
        
        user_id = str(uuid.uuid4())
        password_hash = generate_password_hash(password)
        
        Database.execute_query(
            """INSERT INTO parents (id, email, password_hash, name, role, is_active) 
               VALUES (%s, %s, %s, %s, %s, TRUE)""",
            (user_id, email, password_hash, name, 'parent')
        )
        
        return {
            "success": True,
            "message": "Cadastro realizado com sucesso!",
            "user_id": user_id
        }
    
    def _register_parent_memory(self, email: str, password: str, name: str) -> dict:
        """Registra em memória (fallback)"""
        if email in self._users:
            return {
                "success": False,
                "message": "Este email já está cadastrado"
            }
        
        user_id = str(uuid.uuid4())
        self._users[email] = {
            "id": user_id,
            "email": email,
            "password_hash": generate_password_hash(password),
            "name": name,
            "role": "parent",
            "created_at": datetime.utcnow().isoformat(),
            "children": []
        }
        
        return {
            "success": True,
            "message": "Cadastro realizado com sucesso!",
            "user_id": user_id
        }
    
    # ==================== LOGIN ====================
    
    def login(self, email: str, password: str) -> dict:
        """Autentica um usuário"""
        try:
            use_db = self._use_db()
            print(f"[LOGIN DEBUG] Usando DB: {use_db}, Email: {email}")
            
            if use_db:
                return self._login_db(email, password)
            else:
                return self._login_memory(email, password)
        except Exception as e:
            print(f"[LOGIN DEBUG] Erro: {str(e)}")
            return {
                "success": False,
                "message": "Erro ao fazer login",
                "error": str(e)
            }
    
    def _login_db(self, email: str, password: str) -> dict:
        """Login com banco de dados MySQL"""
        user = Database.execute_query(
            "SELECT id, email, password_hash, name, role FROM parents WHERE email = %s AND is_active = TRUE",
            (email,),
            fetch='one'
        )
        
        print(f"[LOGIN DEBUG] Usuário encontrado no DB: {user is not None}")
        
        if not user or not check_password_hash(user["password_hash"], password):
            print(f"[LOGIN DEBUG] Falha - user exists: {user is not None}")
            return {
                "success": False,
                "message": "Email ou senha incorretos"
            }
        
        # Buscar filhos
        children = Database.execute_query(
            "SELECT id FROM children WHERE parent_id = %s AND is_active = TRUE",
            (user["id"],),
            fetch='all'
        ) or []
        
        children_ids = [c["id"] for c in children]
        
        # Criar tokens JWT
        access_token = create_access_token(
            identity=user["id"],
            additional_claims={
                "email": email,
                "role": user["role"],
                "name": user["name"]
            }
        )
        refresh_token = create_refresh_token(identity=user["id"])
        
        return {
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user["id"],
                "email": email,
                "name": user["name"],
                "children": children_ids
            }
        }
    
    def _login_memory(self, email: str, password: str) -> dict:
        """Login em memória (fallback)"""
        user = self._users.get(email)
        
        if not user or not check_password_hash(user["password_hash"], password):
            return {
                "success": False,
                "message": "Email ou senha incorretos"
            }
        
        access_token = create_access_token(
            identity=user["id"],
            additional_claims={
                "email": email,
                "role": user["role"],
                "name": user["name"]
            }
        )
        refresh_token = create_refresh_token(identity=user["id"])
        
        return {
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user["id"],
                "email": email,
                "name": user["name"],
                "children": user["children"]
            }
        }
    
    # ==================== PERFIS DE CRIANÇAS ====================
    
    def add_child_profile(self, parent_id: str, name: str, age: int, avatar: str = None) -> dict:
        """Adiciona perfil de criança"""
        try:
            # Validar idade
            if age < 4 or age > 12:
                return {
                    "success": False,
                    "message": "Idade deve ser entre 4 e 12 anos"
                }
            
            if self._use_db():
                return self._add_child_db(parent_id, name, age, avatar)
            else:
                return self._add_child_memory(parent_id, name, age, avatar)
                
        except Exception as e:
            return {
                "success": False,
                "message": "Erro ao criar perfil",
                "error": str(e)
            }
    
    def _add_child_db(self, parent_id: str, name: str, age: int, avatar: str) -> dict:
        """Adiciona criança no banco de dados"""
        child_id = str(uuid.uuid4())
        
        Database.execute_query(
            """INSERT INTO children (id, parent_id, name, age, avatar) 
               VALUES (%s, %s, %s, %s, %s)""",
            (child_id, parent_id, name, age, avatar or 'default')
        )
        
        return {
            "success": True,
            "message": f"Perfil de {name} criado com sucesso!",
            "child_id": child_id,
            "profile": {
                "id": child_id,
                "name": name,
                "age": age,
                "avatar": avatar or "default"
            }
        }
    
    def _add_child_memory(self, parent_id: str, name: str, age: int, avatar: str) -> dict:
        """Adiciona criança em memória (fallback)"""
        child_id = str(uuid.uuid4())
        
        self._children_profiles[child_id] = {
            "id": child_id,
            "parent_id": parent_id,
            "name": name,
            "age": age,
            "avatar": avatar or "default",
            "created_at": datetime.utcnow().isoformat(),
            "conversation_history": []
        }
        
        # Adicionar à lista de filhos do responsável
        for email, user in self._users.items():
            if user["id"] == parent_id:
                user["children"].append(child_id)
                break
        
        return {
            "success": True,
            "message": f"Perfil de {name} criado com sucesso!",
            "child_id": child_id,
            "profile": {
                "id": child_id,
                "name": name,
                "age": age,
                "avatar": avatar or "default"
            }
        }
    
    def get_child_profile(self, child_id: str, parent_id: str) -> dict:
        """Obtém perfil de uma criança"""
        try:
            if self._use_db():
                profile = Database.execute_query(
                    "SELECT id, name, age, avatar, parent_id FROM children WHERE id = %s AND is_active = TRUE",
                    (child_id,),
                    fetch='one'
                )
                
                if not profile:
                    return {"success": False, "message": "Perfil não encontrado"}
                
                if profile["parent_id"] != parent_id:
                    return {"success": False, "message": "Acesso negado"}
                
                return {
                    "success": True,
                    "profile": {
                        "id": profile["id"],
                        "name": profile["name"],
                        "age": profile["age"],
                        "avatar": profile["avatar"]
                    }
                }
            else:
                profile = self._children_profiles.get(child_id)
                
                if not profile:
                    return {"success": False, "message": "Perfil não encontrado"}
                
                if profile["parent_id"] != parent_id:
                    return {"success": False, "message": "Acesso negado"}
                
                return {
                    "success": True,
                    "profile": {
                        "id": profile["id"],
                        "name": profile["name"],
                        "age": profile["age"],
                        "avatar": profile["avatar"]
                    }
                }
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def get_children_profiles(self, parent_id: str) -> dict:
        """Lista todos os perfis de crianças de um responsável"""
        try:
            if self._use_db():
                children = Database.execute_query(
                    "SELECT id, name, age, avatar FROM children WHERE parent_id = %s AND is_active = TRUE",
                    (parent_id,),
                    fetch='all'
                ) or []
                
                return {
                    "success": True,
                    "children": children
                }
            else:
                children = []
                for child_id, profile in self._children_profiles.items():
                    if profile["parent_id"] == parent_id:
                        children.append({
                            "id": profile["id"],
                            "name": profile["name"],
                            "age": profile["age"],
                            "avatar": profile["avatar"]
                        })
                
                return {
                    "success": True,
                    "children": children
                }
        except Exception as e:
            return {"success": False, "message": str(e), "children": []}


# Instância global do serviço
auth_service = AuthService()
