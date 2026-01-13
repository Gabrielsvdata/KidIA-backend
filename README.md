# KidIA Backend 🧒🤖

API do chatbot educativo para crianças, desenvolvida com Python e Flask.

## 📋 Sobre o Projeto

O **KidIA** é um chatbot inteligente desenvolvido especialmente para crianças de 4 a 12 anos. Ele oferece uma experiência de conversa segura, educativa e divertida, com linguagem adaptada para o público infantil e filtros de segurança integrados.

---

## Funcionalidades

- ✅ **Chat com IA** adaptado para crianças (4-12 anos)
- ✅ **Filtro de conteúdo** inapropriado automático
- ✅ **Autenticação JWT** para responsáveis
- ✅ **Perfis de crianças** personalizados
- ✅ **Rate limiting** para segurança
- ✅ **Headers de segurança** configurados
- ✅ **Fallback inteligente** (funciona com ou sem banco de dados)

---

## Estrutura do Projeto

```
KidIA backend/
│
├── app.py                  # 🚀 Ponto de entrada da aplicação (Factory Pattern)
├── config.py               # ⚙️ Configurações da aplicação
├── requirements.txt        # 📦 Dependências do projeto
├── setup_database.py       # 🗄️ Script de configuração do banco
│
├── database/               # 🗃️ Camada de banco de dados
│   ├── __init__.py
│   ├── connection.py       # Conexão com MySQL
│   └── schema.sql          # Script de criação das tabelas
│
├── middleware/             # Middlewares de segurança
│   ├── __init__.py
│   └── security.py         # Headers e proteções
│
├── routes/                 # Endpoints da API (Blueprints)
│   ├── __init__.py
│   ├── auth.py             # Rotas de autenticação
│   ├── chat.py             # Rotas do chatbot
│   └── health.py           # Rotas de health check
│
└── services/               # Lógica de negócio
    ├── __init__.py
    ├── auth_service.py     # Serviço de autenticação
    └── chat_service.py     # Serviço do chatbot (Groq API)
```

---

## Descrição dos Arquivos

### 🔹 Arquivos Principais

| Arquivo | Descrição |
|---------|-----------|
| `app.py` | Factory function que cria a aplicação Flask, configura CORS, JWT e registra os blueprints |
| `config.py` | Classes de configuração (Development/Production) com variáveis de ambiente |
| `requirements.txt` | Lista de dependências Python do projeto |

### Database (`/database`)

| Arquivo | Descrição |
|---------|-----------|
| `connection.py` | Classe `Database` com métodos para conexão MySQL e execução de queries |
| `schema.sql` | Script SQL para criar o banco `kidia_db` com tabelas: `parents`, `children`, `conversations`, `messages`, `refresh_tokens` |

### Routes (`/routes`)

| Arquivo | Endpoints | Descrição |
|---------|-----------|-----------|
| `auth.py` | `/api/auth/*` | Registro, login, refresh token, gerenciamento de perfis de crianças |
| `chat.py` | `/api/chat/*` | Envio de mensagens para o chatbot com rate limiting |
| `health.py` | `/api/health` | Verificação de status da API |

### Services (`/services`)

| Arquivo | Descrição |
|---------|-----------|
| `auth_service.py` | Lógica de autenticação, hash de senhas, geração de tokens JWT, CRUD de usuários |
| `chat_service.py` | Integração com Groq API, filtro de conteúdo, prompt do sistema para respostas infantis |

---

## Endpoints da API

### Autenticação (`/api/auth`)

| Método | Rota | Descrição | Auth |
|--------|------|-----------|------|
| `POST` | `/register` | Registra um novo responsável 
| `POST` | `/login` | Autentica e retorna tokens 
| `POST` | `/refresh` | Renova o access token | Refresh 
| `GET` | `/me` | Retorna dados do usuário logado | JWT 
| `POST` | `/children` | Adiciona perfil de criança | JWT 
| `GET` | `/children` | Lista perfis de crianças | JWT 
| `PUT` | `/children/<id>` | Atualiza perfil de criança | JWT 
| `DELETE` | `/children/<id>` | Remove perfil de criança | JWT |

### Chat (`/api/chat`)

| Método | Rota | Descrição | Auth |
|--------|------|-----------|------|
| `POST` | `/message` | Envia mensagem para o chatbot | JWT |
| `POST` | `/quick-message` | Mensagem rápida (sem auth, para testes) | ❌ |

### Health (`/api`)

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/` | Informações da API |
| `GET` | `/health` | Status de saúde da API |

---

## 🚀 Instalação

### 1️ - Criar ambiente virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2 - Instalar dependências

```bash
pip install -r requirements.txt
```

### 3️ - Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz:

```env
# Chaves de segurança
SECRET_KEY=sua-chave-secreta-aqui
JWT_SECRET_KEY=sua-chave-jwt-aqui

# API do Groq (obrigatório para o chat)
GROQ_API_KEY=sua-chave-groq-aqui

# CORS (origens permitidas)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Banco de dados MySQL (opcional)
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=sua-senha
DB_NAME=kidia_db
```

### 4️⃣ Configurar banco de dados (opcional)

```bash
# Execute o schema no MySQL
mysql -u root -p < database/schema.sql
```

> ⚠️ **Nota:** O sistema funciona sem MySQL! Usa memória como fallback.

### 5️⃣ Executar

```bash
# Desenvolvimento
python app.py

# Produção
gunicorn app:create_app() -w 4 -b 0.0.0.0:5000
```

---

## 🔧 Configurações

### Variáveis de Ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `SECRET_KEY` | Chave secreta do Flask | `dev-secret-key` |
| `JWT_SECRET_KEY` | Chave para tokens JWT | `jwt-dev-secret` |
| `GROQ_API_KEY` | Chave da API Groq | - |
| `ALLOWED_ORIGINS` | Origens CORS permitidas | `http://localhost:3000` |
| `FLASK_ENV` | Ambiente (development/production) | `development` |

### Limites de Segurança

| Configuração | Valor | Descrição |
|--------------|-------|-----------|
| `MAX_MESSAGE_LENGTH` | 500 | Tamanho máximo da mensagem |
| `MAX_REQUESTS_PER_MINUTE` | 10 | Rate limit por minuto |
| `MIN_AGE` / `MAX_AGE` | 4-12 | Faixa etária permitida |

---

## 🛡️ Segurança

### Filtro de Conteúdo

O chatbot bloqueia automaticamente temas inapropriados:
- Violência e morte
- Drogas e álcool
- Conteúdo adulto
- Palavrões

### Proteções Implementadas

- ✅ **JWT Authentication** com refresh tokens
- ✅ **Rate Limiting** por usuário
- ✅ **Sanitização de input** (remove caracteres perigosos)
- ✅ **CORS** configurado
- ✅ **Senhas hasheadas** com Werkzeug

---

## 📡 Exemplos de Requisições

### Registrar usuário

```bash
POST /api/auth/register
Content-Type: application/json

{
  "email": "pai@exemplo.com",
  "password": "SenhaForte123",
  "name": "João Silva"
}
```

### Login

```bash
POST /api/auth/login
Content-Type: application/json

{
  "email": "pai@exemplo.com",
  "password": "SenhaForte123"
}
```

### Enviar mensagem

```bash
POST /api/chat/message
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "message": "Por que o céu é azul?",
  "child_id": "uuid-da-crianca"
}
```

---

## 🧪 Testes

### Health Check

```bash
curl http://localhost:5000/api/health
```

### Quick Message (sem auth)

```bash
curl -X POST http://localhost:5000/api/chat/quick-message \
  -H "Content-Type: application/json" \
  -d '{"message": "Olá!"}'
```

---

## 📦 Dependências Principais

| Pacote | Versão | Uso |
|--------|--------|-----|
| Flask | 3.0.0 | Framework web |
| Flask-JWT-Extended | 4.6.0 | Autenticação JWT |
| Flask-CORS | 4.0.0 | Cross-Origin Resource Sharing |
| Groq | - | API de IA (LLM) |
| Werkzeug | 3.0.1 | Hash de senhas |
| Gunicorn | 21.2.0 | Servidor WSGI (produção) |

---

## 🤝 Contribuição

1. Faça um fork do projeto
2. Crie uma branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Add nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

---

## 📄 Licença

Este projeto está sob a licença MIT.

---

## 👨‍💻 Autor

Desenvolvido para crianças aprenderem de forma divertida e segura!
# KidIA-backend
