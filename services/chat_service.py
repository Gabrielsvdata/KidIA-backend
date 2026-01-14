from groq import Groq
from flask import current_app
import re


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
    SYSTEM_PROMPT = """Você é o KidIA, um amiguinho virtual super divertido e inteligente! 🌟

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
    
    def get_response(self, message: str, conversation_history: list = None) -> dict:
        """Gera uma resposta para a mensagem da criança"""
        try:
            # Sanitizar entrada
            clean_message = self.sanitize_input(message)
            
            # Verificar se é segura
            is_safe, warning = self.is_safe_message(clean_message)
            if not is_safe:
                return {
                    "success": True,
                    "response": warning,
                    "filtered": True
                }
            
            # Preparar mensagens para a API
            messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
            
            # Adicionar histórico de conversa (se houver)
            if conversation_history:
                # Limitar histórico para economizar tokens
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
            
            return {
                "success": True,
                "response": assistant_response,
                "filtered": False
            }
            
        except Exception as e:
            return {
                "success": False,
                "response": "Ops! Tive um probleminha. Pode tentar de novo? 🔄",
                "error": str(e)
            }


# Instância global do serviço
chat_service = ChatService()
