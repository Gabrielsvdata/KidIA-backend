# 🧒🤖 KidIA - Chatbot Educativo para Crianças

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Flask-2.0+-green?style=for-the-badge&logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/Groq-LLaMA%203-purple?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Deploy-Render-orange?style=for-the-badge" />
</p>

## 🎯 Sobre o Projeto

O **KidIA** é um assistente virtual inteligente desenvolvido especialmente para crianças de **4 a 12 anos**. Ele oferece uma experiência de conversa **segura, educativa e divertida**, com linguagem adaptada para o público infantil e múltiplas camadas de proteção.

### 🌐 Links do Projeto

| Serviço | URL |
|---------|-----|
| 🖥️ **Frontend** | [https://kid-ia.vercel.app](https://kid-ia.vercel.app) |
| ⚙️ **Backend API** | [https://kidia-backend.onrender.com](https://kidia-backend.onrender.com) |

---

## ✨ Funcionalidades

### Para Crianças 👧👦
- 💬 Chat interativo com IA amigável e educativa
- 🎨 Avatares personalizados para cada perfil
- 📚 Respostas adaptadas por idade (4-12 anos)
- 🛡️ Ambiente 100% seguro e filtrado

### Para Responsáveis 👨‍👩‍👧
- 🔐 Cadastro e login seguro com JWT
- 👶 Criação de múltiplos perfis de crianças
- 🎂 Configuração de idade para respostas personalizadas
- 📊 Controle total sobre os perfis

### Segurança 🔒
- 🚫 Filtro automático de conteúdo inapropriado
- 🍪 Autenticação via cookies HttpOnly
- ⏱️ Rate limiting contra abusos
- 🛡️ Headers de segurança (CORS, CSP, HSTS)

---

## 🛠️ Tecnologias

### Backend
- **Python 3.9+** - Linguagem principal
- **Flask** - Framework web
- **Flask-JWT-Extended** - Autenticação JWT
- **Groq API** - IA (LLaMA 3 70B) - Rápida e gratuita
- **Gunicorn** - Servidor WSGI de produção

### Frontend
- **React** - Biblioteca UI
- **TypeScript** - Tipagem estática
- **Tailwind CSS** - Estilização
- **Vercel** - Deploy e hosting

### Infraestrutura
- **Render** - Hosting do backend
- **MySQL** - Banco de dados (opcional)
- **In-Memory Storage** - Fallback sem banco

---

## 🚀 Como Executar Localmente

### Pré-requisitos
- Python 3.9+
- pip

### Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/Gabrielsvdata/KidIA-backend.git
cd KidIA-backend

# 2. Crie e ative o ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas chaves

# 5. Execute
python app.py
```

### Variáveis de Ambiente

```env
SECRET_KEY=sua-chave-secreta
JWT_SECRET_KEY=sua-chave-jwt
GROQ_API_KEY=sua-chave-groq
ALLOWED_ORIGINS=http://localhost:3000
FLASK_ENV=development
```

---

## 📡 Endpoints da API

### Autenticação `/auth`
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/register` | Cadastra novo responsável |
| POST | `/login` | Faz login (retorna cookies) |
| POST | `/refresh` | Renova token de acesso |
| POST | `/logout` | Faz logout |
| GET | `/me` | Dados do usuário logado |
| POST | `/children` | Cria perfil de criança |
| GET | `/children` | Lista perfis |

### Chat `/chat`
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/message` | Envia mensagem para a IA |

### Health `/`
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/health` | Status da API |

---

## 📁 Estrutura do Projeto

```
KidIA-backend/
├── app.py              # Aplicação Flask (Factory Pattern)
├── config.py           # Configurações (Dev/Prod)
├── gunicorn.conf.py    # Config do servidor
├── requirements.txt    # Dependências
│
├── routes/             # Endpoints da API
│   ├── auth.py         # Autenticação
│   ├── chat.py         # Chat com IA
│   └── health.py       # Health check
│
├── services/           # Lógica de negócio
│   ├── auth_service.py # Autenticação
│   ├── chat_service.py # Integração Groq
│   └── memory_service.py
│
├── middleware/         # Middlewares
│   └── security.py     # CSRF, validações, logs
│
└── database/           # Banco de dados
    ├── connection.py   # Conexão MySQL
    └── schema.sql      # Schema das tabelas
```

---

## 👨‍💻 Autor

**Gabriel** - [GitHub](https://github.com/Gabrielsvdata)

---

## 📄 Licença

Este projeto está sob a licença MIT.

---

<p align="center">
  Feito com 💜 para ajudar crianças a aprenderem de forma divertida e segura!
</p>
