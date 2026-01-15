-- =====================================================
-- MIGRAÇÃO: Sistema de Memória Persistente para o Kiko
-- Execute este script APÓS o schema.sql inicial
-- =====================================================

USE kidia_db;

-- =====================================================
-- ADICIONAR CAMPO DE CONTEXTO DE MEMÓRIA NA TABELA CHILDREN
-- Armazena informações importantes que o Kiko deve lembrar
-- =====================================================
ALTER TABLE children 
ADD COLUMN IF NOT EXISTS memory_context JSON DEFAULT '{}' 
COMMENT 'Contexto de memória: nome, interesses, preferências';

-- =====================================================
-- TABELA: parent_alerts (Alertas para os Pais)
-- Armazena perguntas sensíveis/perigosas para os pais verem
-- =====================================================
CREATE TABLE IF NOT EXISTS parent_alerts (
    id VARCHAR(36) PRIMARY KEY,
    child_id VARCHAR(36) NOT NULL,
    alert_type ENUM('pergunta_sensivel', 'tema_bloqueado', 'comportamento', 'outro') NOT NULL,
    severity ENUM('baixa', 'media', 'alta') DEFAULT 'media',
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL COMMENT 'Descrição do alerta',
    original_message TEXT NOT NULL COMMENT 'Mensagem original da criança',
    kiko_response TEXT COMMENT 'Como o Kiko respondeu',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    was_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP NULL,
    
    FOREIGN KEY (child_id) REFERENCES children(id) ON DELETE CASCADE,
    INDEX idx_child_id (child_id),
    INDEX idx_created_at (created_at),
    INDEX idx_was_read (was_read),
    INDEX idx_alert_type (alert_type)
) ENGINE=InnoDB;

-- =====================================================
-- TABELA: conversation_sessions (Sessões de Conversa)
-- Gerencia sessões ativas de conversa com histórico recente
-- =====================================================
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id VARCHAR(36) PRIMARY KEY,
    child_id VARCHAR(36) NOT NULL,
    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_end TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    message_count INT DEFAULT 0,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (child_id) REFERENCES children(id) ON DELETE CASCADE,
    INDEX idx_child_id (child_id),
    INDEX idx_is_active (is_active),
    INDEX idx_last_activity (last_activity)
) ENGINE=InnoDB;

-- =====================================================
-- TABELA: session_messages (Mensagens da Sessão)
-- Histórico recente de mensagens para contexto do Kiko
-- =====================================================
CREATE TABLE IF NOT EXISTS session_messages (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    role ENUM('user', 'assistant') NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (session_id) REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB;

-- =====================================================
-- VIEW: Alertas não lidos por pai
-- =====================================================
CREATE OR REPLACE VIEW v_unread_alerts_by_parent AS
SELECT 
    p.id AS parent_id,
    p.email AS parent_email,
    c.id AS child_id,
    c.name AS child_name,
    pa.id AS alert_id,
    pa.alert_type,
    pa.severity,
    pa.title,
    pa.content,
    pa.original_message,
    pa.created_at
FROM parent_alerts pa
JOIN children c ON pa.child_id = c.id
JOIN parents p ON c.parent_id = p.id
WHERE pa.was_read = FALSE
ORDER BY pa.created_at DESC;

-- =====================================================
-- PROCEDURE: Limpar sessões antigas (manutenção)
-- =====================================================
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS cleanup_old_sessions()
BEGIN
    -- Encerrar sessões inativas há mais de 30 minutos
    UPDATE conversation_sessions 
    SET is_active = FALSE, session_end = NOW()
    WHERE is_active = TRUE 
    AND last_activity < DATE_SUB(NOW(), INTERVAL 30 MINUTE);
    
    -- Deletar mensagens de sessões com mais de 7 dias
    DELETE sm FROM session_messages sm
    JOIN conversation_sessions cs ON sm.session_id = cs.id
    WHERE cs.session_end < DATE_SUB(NOW(), INTERVAL 7 DAY);
    
    -- Deletar sessões encerradas com mais de 30 dias
    DELETE FROM conversation_sessions 
    WHERE is_active = FALSE 
    AND session_end < DATE_SUB(NOW(), INTERVAL 30 DAY);
END //
DELIMITER ;

-- =====================================================
-- EVENT: Executar limpeza automaticamente (opcional)
-- Requer event_scheduler habilitado no MySQL
-- =====================================================
-- SET GLOBAL event_scheduler = ON;
-- CREATE EVENT IF NOT EXISTS evt_cleanup_sessions
-- ON SCHEDULE EVERY 1 HOUR
-- DO CALL cleanup_old_sessions();
