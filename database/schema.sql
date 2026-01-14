-- =====================================================
-- BANCO DE DADOS KIDIA - Script de Criação
-- Execute este script no MySQL para criar o banco
-- =====================================================

-- Criar o banco de dados
CREATE DATABASE IF NOT EXISTS kidia_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE kidia_db;

-- =====================================================
-- TABELA: parents (Responsáveis)
-- =====================================================
CREATE TABLE IF NOT EXISTS parents (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(20) DEFAULT 'parent',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    INDEX idx_email (email),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB;

-- =====================================================
-- TABELA: children (Perfis das Crianças)
-- =====================================================
CREATE TABLE IF NOT EXISTS children (
    id VARCHAR(36) PRIMARY KEY,
    parent_id VARCHAR(36) NOT NULL,
    name VARCHAR(100) NOT NULL,
    age INT NOT NULL CHECK (age >= 4 AND age <= 12),
    avatar VARCHAR(50) DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    FOREIGN KEY (parent_id) REFERENCES parents(id) ON DELETE CASCADE,
    INDEX idx_parent_id (parent_id)
) ENGINE=InnoDB;

-- =====================================================
-- TABELA: conversations (Histórico de Conversas)
-- =====================================================
CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(36) PRIMARY KEY,
    child_id VARCHAR(36) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    
    FOREIGN KEY (child_id) REFERENCES children(id) ON DELETE CASCADE,
    INDEX idx_child_id (child_id),
    INDEX idx_started_at (started_at)
) ENGINE=InnoDB;

-- =====================================================
-- TABELA: messages (Mensagens das Conversas)
-- =====================================================
CREATE TABLE IF NOT EXISTS messages (
    id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL,
    role ENUM('user', 'assistant') NOT NULL,
    content TEXT NOT NULL,
    was_filtered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB;

-- =====================================================
-- TABELA: refresh_tokens (Tokens de Renovação)
-- =====================================================
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id VARCHAR(36) PRIMARY KEY,
    parent_id VARCHAR(36) NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked BOOLEAN DEFAULT FALSE,
    
    FOREIGN KEY (parent_id) REFERENCES parents(id) ON DELETE CASCADE,
    INDEX idx_parent_id (parent_id),
    INDEX idx_token_hash (token_hash)
) ENGINE=InnoDB;

-- =====================================================
-- DADOS DE TESTE (opcional)
-- =====================================================
-- Descomente para inserir um usuário de teste
-- Senha: Teste123!

-- INSERT INTO parents (id, email, password_hash, name) VALUES (
--     'test-user-001',
--     'teste@kidia.com',
--     'scrypt:32768:8:1$...',  -- Hash gerado pelo Werkzeug
--     'Usuário Teste'
-- );
