"""
Serviço de Memória Persistente para o Kiko
==========================================
Gerencia duas camadas de memória:
1. Contexto permanente (nome, interesses, preferências)
2. Histórico de conversa recente (últimas mensagens da sessão)
"""

from database.connection import Database
import json
import uuid
import re
from datetime import datetime


class MemoryService:
    """Serviço para gerenciar memória persistente do chatbot"""
    
    # Padrões para extrair informações importantes das mensagens
    EXTRACTION_PATTERNS = {
        'nome': [
            r'(?:meu nome é|me chamo|pode me chamar de|sou o|sou a)\s+([A-Za-zÀ-ÿ]+)',
            r'(?:eu sou|eu me chamo)\s+([A-Za-zÀ-ÿ]+)',
        ],
        'idade': [
            r'(?:tenho|eu tenho|fiz)\s+(\d+)\s+anos?',
            r'(\d+)\s+anos?(?:\s+de idade)?',
        ],
        'cor_favorita': [
            r'(?:minha cor favorita é|gosto (?:da cor|de)|adoro a cor)\s+([A-Za-zÀ-ÿ]+)',
            r'(?:cor favorita)[:\s]+([A-Za-zÀ-ÿ]+)',
        ],
        'animal_favorito': [
            r'(?:meu animal favorito é|gosto de|adoro)\s+([A-Za-zÀ-ÿ]+s?)',
            r'(?:animal favorito)[:\s]+([A-Za-zÀ-ÿ]+)',
        ],
        'interesses': [
            r'(?:gosto de|adoro|amo)\s+(.+?)(?:\.|!|\?|$)',
            r'(?:meu favorito é|minha favorita é)\s+(.+?)(?:\.|!|\?|$)',
        ]
    }
    
    # Perguntas sensíveis que devem alertar os pais
    SENSITIVE_PATTERNS = [
        {
            'pattern': r'(?:de onde|como)\s+(?:vem|vêm|surgem?)\s+(?:os\s+)?beb[êe]s?',
            'type': 'pergunta_sensivel',
            'severity': 'media',
            'title': 'Pergunta sobre origem dos bebês'
        },
        {
            'pattern': r'(?:por que|porque)\s+(?:as pessoas|alguém|a gente)\s+morr?e',
            'type': 'pergunta_sensivel',
            'severity': 'media',
            'title': 'Pergunta sobre morte'
        },
        {
            'pattern': r'(?:meus pais|papai e mamãe|meu pai|minha mãe)\s+(?:vão\s+)?(?:separar|divorciar|brigar)',
            'type': 'pergunta_sensivel',
            'severity': 'alta',
            'title': 'Preocupação com separação dos pais'
        },
        {
            'pattern': r'(?:estou|tô|to)\s+(?:triste|com medo|assustado|preocupado)',
            'type': 'comportamento',
            'severity': 'media',
            'title': 'Criança expressando sentimentos negativos'
        },
        {
            'pattern': r'(?:ninguém|nenhum amigo|sozinho|não tenho amigos)',
            'type': 'comportamento',
            'severity': 'media',
            'title': 'Possível isolamento social'
        },
        {
            'pattern': r'(?:me batem|me machucam|me xingam|bullying)',
            'type': 'comportamento',
            'severity': 'alta',
            'title': 'Possível bullying ou maus tratos'
        },
        {
            'pattern': r'(?:quero\s+)?(?:sumir|desaparecer|fugir|ir embora)',
            'type': 'comportamento',
            'severity': 'alta',
            'title': 'Criança querendo fugir/desaparecer'
        },
        {
            'pattern': r'(?:o que é|como funciona)\s+(?:sexo|drogas?|cigarro|bebida alcoólica)',
            'type': 'pergunta_sensivel',
            'severity': 'media',
            'title': 'Pergunta sobre temas adultos'
        }
    ]
    
    def __init__(self):
        pass
    
    # =========================================
    # GESTÃO DE SESSÕES
    # =========================================
    
    def get_or_create_session(self, child_id: str) -> str:
        """Obtém sessão ativa ou cria uma nova"""
        # Buscar sessão ativa
        query = """
            SELECT id FROM conversation_sessions 
            WHERE child_id = %s AND is_active = TRUE
            ORDER BY last_activity DESC LIMIT 1
        """
        result = Database.execute_query(query, (child_id,), fetch='one')
        
        if result:
            return result['id']
        
        # Criar nova sessão
        session_id = str(uuid.uuid4())
        insert_query = """
            INSERT INTO conversation_sessions (id, child_id)
            VALUES (%s, %s)
        """
        Database.execute_query(insert_query, (session_id, child_id))
        return session_id
    
    def end_session(self, session_id: str):
        """Encerra uma sessão de conversa"""
        query = """
            UPDATE conversation_sessions 
            SET is_active = FALSE, session_end = NOW()
            WHERE id = %s
        """
        Database.execute_query(query, (session_id,))
    
    # =========================================
    # HISTÓRICO DE MENSAGENS (MEMÓRIA CURTA)
    # =========================================
    
    def save_message(self, session_id: str, role: str, content: str):
        """Salva uma mensagem no histórico da sessão"""
        message_id = str(uuid.uuid4())
        query = """
            INSERT INTO session_messages (id, session_id, role, content)
            VALUES (%s, %s, %s, %s)
        """
        Database.execute_query(query, (message_id, session_id, role, content))
        
        # Atualizar contador de mensagens
        update_query = """
            UPDATE conversation_sessions 
            SET message_count = message_count + 1
            WHERE id = %s
        """
        Database.execute_query(update_query, (session_id,))
    
    def get_recent_messages(self, session_id: str, limit: int = 10) -> list:
        """Obtém as últimas mensagens da sessão para contexto"""
        query = """
            SELECT role, content FROM session_messages
            WHERE session_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        results = Database.execute_query(query, (session_id, limit), fetch='all')
        
        if not results:
            return []
        
        # Inverter para ordem cronológica
        messages = [{"role": r['role'], "content": r['content']} for r in reversed(results)]
        return messages
    
    # =========================================
    # CONTEXTO PERMANENTE (MEMÓRIA LONGA)
    # =========================================
    
    def get_memory_context(self, child_id: str) -> dict:
        """Obtém o contexto de memória permanente da criança"""
        query = "SELECT memory_context, name, age FROM children WHERE id = %s"
        result = Database.execute_query(query, (child_id,), fetch='one')
        
        if not result:
            return {}
        
        context = result.get('memory_context', {})
        if isinstance(context, str):
            try:
                context = json.loads(context)
            except:
                context = {}
        
        # Garantir que o nome e idade do cadastro estejam no contexto
        if not context.get('nome') and result.get('name'):
            context['nome'] = result['name']
        if not context.get('idade') and result.get('age'):
            context['idade'] = result['age']
            
        return context
    
    def update_memory_context(self, child_id: str, updates: dict):
        """Atualiza o contexto de memória permanente"""
        # Obter contexto atual
        current_context = self.get_memory_context(child_id)
        
        # Mesclar atualizações
        for key, value in updates.items():
            if key == 'interesses':
                # Interesses são uma lista, adicionar sem duplicar
                current_interests = current_context.get('interesses', [])
                if isinstance(value, list):
                    for interest in value:
                        if interest not in current_interests:
                            current_interests.append(interest)
                elif value not in current_interests:
                    current_interests.append(value)
                current_context['interesses'] = current_interests[-10:]  # Limitar a 10
            else:
                current_context[key] = value
        
        # Salvar no banco
        query = "UPDATE children SET memory_context = %s WHERE id = %s"
        Database.execute_query(query, (json.dumps(current_context, ensure_ascii=False), child_id))
        
        return current_context
    
    def extract_info_from_message(self, message: str) -> dict:
        """Extrai informações importantes de uma mensagem"""
        extracted = {}
        message_lower = message.lower()
        
        for info_type, patterns in self.EXTRACTION_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, message_lower, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if info_type == 'idade':
                        try:
                            value = int(value)
                        except:
                            continue
                    extracted[info_type] = value
                    break
        
        return extracted
    
    # =========================================
    # ALERTAS PARA OS PAIS
    # =========================================
    
    def check_sensitive_content(self, message: str) -> dict | None:
        """Verifica se a mensagem contém conteúdo sensível"""
        message_lower = message.lower()
        
        for sensitive in self.SENSITIVE_PATTERNS:
            if re.search(sensitive['pattern'], message_lower, re.IGNORECASE):
                return {
                    'type': sensitive['type'],
                    'severity': sensitive['severity'],
                    'title': sensitive['title']
                }
        
        return None
    
    def create_parent_alert(self, child_id: str, alert_type: str, severity: str, 
                           title: str, content: str, original_message: str, 
                           kiko_response: str = None):
        """Cria um alerta para os pais"""
        alert_id = str(uuid.uuid4())
        query = """
            INSERT INTO parent_alerts 
            (id, child_id, alert_type, severity, title, content, original_message, kiko_response)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        Database.execute_query(query, (
            alert_id, child_id, alert_type, severity, 
            title, content, original_message, kiko_response
        ))
        return alert_id
    
    def get_unread_alerts(self, parent_id: str) -> list:
        """Obtém alertas não lidos de um pai"""
        query = """
            SELECT pa.*, c.name as child_name
            FROM parent_alerts pa
            JOIN children c ON pa.child_id = c.id
            WHERE c.parent_id = %s AND pa.was_read = FALSE
            ORDER BY pa.created_at DESC
        """
        return Database.execute_query(query, (parent_id,), fetch='all') or []
    
    def get_all_alerts(self, parent_id: str, limit: int = 50) -> list:
        """Obtém todos os alertas de um pai"""
        query = """
            SELECT pa.*, c.name as child_name
            FROM parent_alerts pa
            JOIN children c ON pa.child_id = c.id
            WHERE c.parent_id = %s
            ORDER BY pa.created_at DESC
            LIMIT %s
        """
        return Database.execute_query(query, (parent_id, limit), fetch='all') or []
    
    def mark_alert_as_read(self, alert_id: str, parent_id: str) -> bool:
        """Marca um alerta como lido (verificando se pertence ao pai)"""
        query = """
            UPDATE parent_alerts pa
            JOIN children c ON pa.child_id = c.id
            SET pa.was_read = TRUE, pa.read_at = NOW()
            WHERE pa.id = %s AND c.parent_id = %s
        """
        result = Database.execute_query(query, (alert_id, parent_id))
        return result > 0
    
    def mark_all_alerts_as_read(self, parent_id: str) -> int:
        """Marca todos os alertas de um pai como lidos"""
        query = """
            UPDATE parent_alerts pa
            JOIN children c ON pa.child_id = c.id
            SET pa.was_read = TRUE, pa.read_at = NOW()
            WHERE c.parent_id = %s AND pa.was_read = FALSE
        """
        return Database.execute_query(query, (parent_id,))
    
    # =========================================
    # CONSTRUÇÃO DO CONTEXTO PARA O PROMPT
    # =========================================
    
    def build_context_prompt(self, child_id: str) -> str:
        """Constrói o prompt de contexto baseado na memória permanente"""
        context = self.get_memory_context(child_id)
        
        if not context:
            return ""
        
        parts = ["\n\nINFORMAÇÕES SOBRE ESTA CRIANÇA (use naturalmente na conversa):"]
        
        if context.get('nome'):
            parts.append(f"- Nome da criança: {context['nome']}")
        
        if context.get('idade'):
            parts.append(f"- Idade: {context['idade']} anos")
        
        if context.get('cor_favorita'):
            parts.append(f"- Cor favorita: {context['cor_favorita']}")
        
        if context.get('animal_favorito'):
            parts.append(f"- Animal favorito: {context['animal_favorito']}")
        
        if context.get('interesses'):
            interesses = ', '.join(context['interesses'][:5])
            parts.append(f"- Coisas que gosta: {interesses}")
        
        if len(parts) > 1:
            parts.append("\nUse essas informações para personalizar a conversa e mostrar que você lembra dela!")
            return '\n'.join(parts)
        
        return ""


# Instância global do serviço
memory_service = MemoryService()
