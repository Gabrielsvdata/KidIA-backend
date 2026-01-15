"""
Script para executar migrações do banco de dados
================================================
Execute este script após configurar o banco inicial (schema.sql)
"""

import os
import sys
from pathlib import Path

# Adicionar o diretório pai ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import Database


def run_migration(migration_file: str):
    """Executa um arquivo de migração SQL"""
    print(f"\n📦 Executando migração: {migration_file}")
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Separar comandos (por ponto e vírgula, mas cuidado com DELIMITER)
    # Para simplicidade, vamos executar comando por comando
    statements = []
    current_statement = ""
    delimiter = ";"
    
    for line in sql_content.split('\n'):
        stripped = line.strip()
        
        # Ignorar comentários
        if stripped.startswith('--') or stripped.startswith('#'):
            continue
        
        # Verificar mudança de delimiter
        if stripped.upper().startswith('DELIMITER'):
            delimiter = stripped.split()[1]
            continue
        
        current_statement += line + "\n"
        
        if stripped.endswith(delimiter):
            # Remove o delimiter do final
            statement = current_statement.strip()
            if delimiter != ";":
                statement = statement[:-len(delimiter)]
            if statement:
                statements.append(statement)
            current_statement = ""
    
    # Executar cada statement
    success_count = 0
    error_count = 0
    
    for i, statement in enumerate(statements):
        if not statement.strip():
            continue
            
        try:
            # Mostrar prévia do comando
            preview = statement[:50].replace('\n', ' ')
            print(f"  [{i+1}/{len(statements)}] {preview}...")
            
            Database.execute_query(statement)
            success_count += 1
            
        except Exception as e:
            error_msg = str(e)
            # Ignorar erros de "já existe"
            if 'Duplicate' in error_msg or 'already exists' in error_msg:
                print(f"    ⚠️  Já existe (ignorando)")
                success_count += 1
            else:
                print(f"    ❌ Erro: {error_msg}")
                error_count += 1
    
    print(f"\n✅ Migração concluída: {success_count} sucesso, {error_count} erros")
    return error_count == 0


def main():
    """Executa todas as migrações pendentes"""
    migrations_dir = Path(__file__).parent / 'migrations'
    
    if not migrations_dir.exists():
        print("❌ Diretório de migrações não encontrado")
        return
    
    # Listar arquivos de migração em ordem
    migration_files = sorted(migrations_dir.glob('*.sql'))
    
    if not migration_files:
        print("ℹ️  Nenhuma migração encontrada")
        return
    
    print("🚀 Iniciando migrações do KidIA")
    print(f"   Encontradas {len(migration_files)} migração(ões)")
    
    # Testar conexão primeiro
    success, msg = Database.test_connection()
    if not success:
        print(f"❌ Erro de conexão: {msg}")
        print("   Certifique-se de que o MySQL está rodando e configurado corretamente")
        return
    
    print("✅ Conexão com banco OK")
    
    # Executar cada migração
    for migration_file in migration_files:
        run_migration(str(migration_file))
    
    print("\n🎉 Todas as migrações foram processadas!")


if __name__ == '__main__':
    main()
