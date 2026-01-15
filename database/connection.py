"""
Database Connection - Otimizado para Render
============================================
Pool de conexões com lazy loading para reduzir cold start
"""

import mysql.connector
from mysql.connector import pooling
from flask import g
import os


class Database:
    """Gerenciador de conexão com MySQL - Lazy Loading"""
    
    _pool = None
    
    @classmethod
    def get_pool(cls):
        """Obtém ou cria o pool de conexões (lazy loading)"""
        if cls._pool is None:
            cls._pool = pooling.MySQLConnectionPool(
                pool_name="kidia_pool",
                pool_size=3,  # Reduzido para economizar RAM no Render
                pool_reset_session=True,
                host=os.getenv('MYSQL_HOST', 'localhost'),
                port=int(os.getenv('MYSQL_PORT', 3306)),
                user=os.getenv('MYSQL_USER', 'root'),
                password=os.getenv('MYSQL_PASSWORD', ''),
                database=os.getenv('MYSQL_DATABASE', 'kidia_db'),
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci',
                connect_timeout=10
            )
        return cls._pool
    
    @classmethod
    def get_connection(cls):
        """Obtém uma conexão do pool"""
        return cls.get_pool().get_connection()
    
    @classmethod
    def execute_query(cls, query: str, params: tuple = None, fetch: str = None):
        """
        Executa uma query no banco de dados.
        
        Args:
            query: Query SQL
            params: Parâmetros da query
            fetch: 'one' para fetchone, 'all' para fetchall, None para execute
        """
        conn = None
        cursor = None
        try:
            conn = cls.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            
            if fetch == 'one':
                result = cursor.fetchone()
            elif fetch == 'all':
                result = cursor.fetchall()
            else:
                conn.commit()
                result = cursor.lastrowid or cursor.rowcount
            
            return result
            
        except mysql.connector.Error as e:
            if conn:
                conn.rollback()
            raise e
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @classmethod
    def test_connection(cls):
        """Testa a conexão com o banco"""
        try:
            conn = cls.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()
            return True, "Conexão OK"
        except Exception as e:
            return False, str(e)


# Funções auxiliares para uso direto
def get_db():
    """Obtém conexão do banco para o contexto atual"""
    if 'db' not in g:
        g.db = Database.get_connection()
    return g.db


def close_db(e=None):
    """Fecha a conexão do banco"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(app):
    """Inicializa o banco de dados com a aplicação Flask"""
    app.teardown_appcontext(close_db)
