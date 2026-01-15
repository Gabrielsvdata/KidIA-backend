from groq import Groq
from flask import current_app
import re
from services.memory_service import memory_service


class ChatService:
    """Serviço para gerenciar conversas do chatbot infantil usando Groq"""
    
    # Palavras e temas inapropriados para filtrar
    BLOCKED_TOPICS = [
        'violência', 'violencia', 'matar', 'morte', 'morrer',
        'drogas', 'álcool', 'alcool', 'cigarro', 'bebida',
        'palavrão', 'palavrao', 'xingamento',
        'sexo', 'sexual', 'adulto',
        'arma', 'tiro', 'sangue'
    ]
    
    # Prompt do sistema para respostas infantis
    SYSTEM_PROMPT = """Você é o Kiko, um amiguinho virtual super divertido e inteligente! 🌟

SUA PERSONALIDADE:
- Você é como um amigo mais velho legal que sabe explicar as coisas de um jeito fácil
- Você adora curiosidades, brincadeiras e aprender coisas novas junto com as crianças
- Você usa palavras simples e divertidas
- Você é animado, carinhoso e sempre positivo!

COMO VOCÊ FALA:
- Use frases curtas e fáceis (máximo 2-3 frases por resposta)
- Use emojis para deixar tudo mais legal! 🎨🦄⭐🌈🚀
- Fale como se estivesse conversando com um amiguinho
- Use expressões como "Que legal!", "Uau!", "Sabia que...", "Adivinha só!"
- Faça perguntas para manter a conversa animada

EXEMPLOS DE COMO RESPONDER:
- "Que pergunta incrível! 🌟 Sabia que..."
- "Uau, você é muito curioso! 🦄 Deixa eu te contar..."
- "Boa pergunta, amiguinho! 🚀"

REGRAS DE SEGURANÇA:
- NUNCA fale sobre coisas de adulto, violência ou coisas assustadoras
- Se perguntarem algo estranho, diga: "Hmm, que tal perguntar isso pros seus pais? Eles vão adorar explicar! 💜"
- Sempre incentive a criança a conversar com os pais sobre dúvidas importantes
- Seja sempre gentil e acolhedor

IMPORTANTE: Suas respostas devem ser CURTAS (2-3 frases no máximo) e SUPER FÁCEIS de entender!"""

    def __init__(self):
        self.client = None
    
    def _get_client(self):
        """Obtém o cliente Groq de forma lazy"""
        if self.client is None:
            api_key = current_app.config.get('GROQ_API_KEY')
            if not api_key:
                raise ValueError("GROQ_API_KEY não configurada")
            self.client = Groq(api_key=api_key)
        return self.client
    
    def is_safe_message(self, message: str) -> tuple[bool, str]:
        """Verifica se a mensagem é apropriada para crianças"""
        message_lower = message.lower()
        
        for topic in self.BLOCKED_TOPICS:
            if topic in message_lower:
                return False, f"Hmm, vamos conversar sobre outra coisa? 🌈"
        
        return True, ""
    
    def sanitize_input(self, message: str) -> str:
        """Limpa e sanitiza a entrada do usuário"""
        # Remove caracteres especiais perigosos
        message = re.sub(r'[<>{}[\]\\]', '', message)
        # Limita o tamanho
        max_length = current_app.config.get('MAX_MESSAGE_LENGTH', 500)
        return message[:max_length].strip()
    
    def get_response(self, message: str, child_id: str = None, conversation_history: list = None) -> dict:
        """
        Gera uma resposta para a mensagem da criança.
        
        Args:
            message: Mensagem da criança
            child_id: ID da criança (para memória persistente)
            conversation_history: Histórico manual (fallback se não tiver child_id)
        """
        try:
            # Sanitizar entrada
            clean_message = self.sanitize_input(message)
            
            # Verificar se é segura
            is_safe, warning = self.is_safe_message(clean_message)
            
            # Variáveis para controle de alertas
            sensitive_alert = None
            session_id = None
            
            # Se temos child_id, usar memória persistente
            if child_id:
                # Obter ou criar sessão
                session_id = memory_service.get_or_create_session(child_id)
                
                # Verificar conteúdo sensível e criar alerta se necessário
                sensitive_alert = memory_service.check_sensitive_content(clean_message)
                
                # Extrair informações importantes da mensagem
                extracted_info = memory_service.extract_info_from_message(clean_message)
                if extracted_info:
                    memory_service.update_memory_context(child_id, extracted_info)
                
                # Salvar mensagem do usuário
                memory_service.save_message(session_id, 'user', clean_message)
            
            # Se mensagem não é segura, retornar aviso
            if not is_safe:
                response_text = warning
                
                # Criar alerta para mensagem bloqueada
                if child_id and session_id:
                    memory_service.create_parent_alert(
                        child_id=child_id,
                        alert_type='tema_bloqueado',
                        severity='media',
                        title='Mensagem com tema bloqueado',
                        content=f'A criança tentou falar sobre um tema bloqueado.',
                        original_message=clean_message,
                        kiko_response=response_text
                    )
                    memory_service.save_message(session_id, 'assistant', response_text)
                
                return {
                    "success": True,
                    "response": response_text,
                    "filtered": True
                }
            
            # Preparar prompt do sistema com contexto de memória
            system_prompt = self.SYSTEM_PROMPT
            if child_id:
                context_prompt = memory_service.build_context_prompt(child_id)
                if context_prompt:
                    system_prompt += context_prompt
            
            # Preparar mensagens para a API
            messages = [{"role": "system", "content": system_prompt}]
            
            # Adicionar histórico de conversa
            if child_id and session_id:
                # Usar histórico da sessão (memória persistente)
                recent_history = memory_service.get_recent_messages(session_id, limit=8)
                # Excluir a última mensagem pois é a atual que acabamos de salvar
                if recent_history:
                    messages.extend(recent_history[:-1])
            elif conversation_history:
                # Fallback para histórico manual
                recent_history = conversation_history[-6:]
                messages.extend(recent_history)
            
            # Adicionar mensagem atual
            messages.append({"role": "user", "content": clean_message})
            
            # Chamar a API Groq
            client = self._get_client()
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=300,
                temperature=0.7
            )
            
            assistant_response = response.choices[0].message.content
            
            # Verificar se a resposta também é segura
            is_response_safe, _ = self.is_safe_message(assistant_response)
            if not is_response_safe:
                assistant_response = "Que tal conversarmos sobre outra coisa divertida? O que você gosta de fazer? 🎨"
            
            # Salvar resposta do assistente na sessão
            if child_id and session_id:
                memory_service.save_message(session_id, 'assistant', assistant_response)
                
                # Criar alerta se mensagem era sensível
                if sensitive_alert:
                    memory_service.create_parent_alert(
                        child_id=child_id,
                        alert_type=sensitive_alert['type'],
                        severity=sensitive_alert['severity'],
                        title=sensitive_alert['title'],
                        content=f"A criança fez uma pergunta/comentário que pode precisar de atenção.",
                        original_message=clean_message,
                        kiko_response=assistant_response
                    )
            
            return {
                "success": True,
                "response": assistant_response,
                "filtered": False,
                "session_id": session_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "response": "Ops! Tive um probleminha. Pode tentar de novo? 🔄",
                "error": str(e)
            }


# Instância global do serviço
chat_service = ChatService()
