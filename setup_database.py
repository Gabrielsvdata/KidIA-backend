"""
Script para configurar o banco de dados MySQL do KidIA
Execute: python setup_database.py
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()


def create_database():
    """Cria o banco de dados e as tabelas"""
    import mysql.connector
    
    # Configurações
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = int(os.getenv('MYSQL_PORT', 3306))
    user = os.getenv('MYSQL_USER', 'root')
    password = os.getenv('MYSQL_PASSWORD', '')
    database = os.getenv('MYSQL_DATABASE', 'kidia_db')
    
    print(f"🔌 Conectando ao MySQL em {host}:{port}...")
    
    try:
        # Conectar sem especificar banco
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password
        )
        cursor = conn.cursor()
        
        # Criar banco de dados
        print(f"📦 Criando banco de dados '{database}'...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE {database}")
        
        # Criar tabela parents
        print("👤 Criando tabela 'parents'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parents (
                id VARCHAR(36) PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                name VARCHAR(100) NOT NULL,
                role VARCHAR(20) DEFAULT 'parent',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                INDEX idx_email (email)
            ) ENGINE=InnoDB
        """)
        
        # Criar tabela children
        print("👶 Criando tabela 'children'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS children (
                id VARCHAR(36) PRIMARY KEY,
                parent_id VARCHAR(36) NOT NULL,
                name VARCHAR(100) NOT NULL,
                age INT NOT NULL,
                avatar VARCHAR(50) DEFAULT 'default',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (parent_id) REFERENCES parents(id) ON DELETE CASCADE,
                INDEX idx_parent_id (parent_id)
            ) ENGINE=InnoDB
        """)
        
        # Criar tabela conversations
        print("💬 Criando tabela 'conversations'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id VARCHAR(36) PRIMARY KEY,
                child_id VARCHAR(36) NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP NULL,
                FOREIGN KEY (child_id) REFERENCES children(id) ON DELETE CASCADE,
                INDEX idx_child_id (child_id)
            ) ENGINE=InnoDB
        """)
        
        # Criar tabela messages
        print("📝 Criando tabela 'messages'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id VARCHAR(36) PRIMARY KEY,
                conversation_id VARCHAR(36) NOT NULL,
                role ENUM('user', 'assistant') NOT NULL,
                content TEXT NOT NULL,
                was_filtered BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                INDEX idx_conversation_id (conversation_id)
            ) ENGINE=InnoDB
        """)
        
        conn.commit()
        
        print("\n✅ Banco de dados configurado com sucesso!")
        print(f"   Database: {database}")
        print(f"   Host: {host}:{port}")
        print(f"   User: {user}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except mysql.connector.Error as e:
        print(f"\n❌ Erro ao configurar banco de dados: {e}")
        print("\n📋 Verifique:")
        print("   1. O MySQL está rodando?")
        print("   2. As credenciais no .env estão corretas?")
        print("   3. O usuário tem permissão para criar banco?")
        return False


def test_connection():
    """Testa a conexão com o banco"""
    print("\n🧪 Testando conexão...")
    
    try:
        from database.connection import Database
        ok, msg = Database.test_connection()
        
        if ok:
            print("✅ Conexão OK!")
        else:
            print(f"❌ Falha: {msg}")
            
        return ok
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


if __name__ == '__main__':
    print("=" * 50)
    print("  🧒 KidIA - Configuração do Banco de Dados")
    print("=" * 50)
    print()
    
    if create_database():
        test_connection()
    
    print()
    print("=" * 50)
