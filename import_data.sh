#!/bin/bash

# Script para importar dados do SQLite para PostgreSQL
# Uso: ./import_data.sh

set -e  # Parar em caso de erro

echo "🔄 Importação de Dados para PostgreSQL"
echo "======================================"
echo ""

# Verificar se DATABASE_URL está configurada
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERRO: Variável DATABASE_URL não está configurada!"
    echo ""
    echo "Configure a variável de ambiente primeiro:"
    echo "  export DATABASE_URL='postgresql://user:pass@host:port/dbname'"
    echo ""
    echo "Para obter a URL:"
    echo "  1. Acesse Railway Dashboard"
    echo "  2. Entre no serviço PostgreSQL"
    echo "  3. Aba 'Variables' → copie DATABASE_URL"
    exit 1
fi

# Verificar se o backup existe
if [ ! -f "backup_data.json" ]; then
    echo "❌ ERRO: Arquivo backup_data.json não encontrado!"
    echo ""
    echo "Crie o backup primeiro:"
    echo "  python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 2 -o backup_data.json"
    exit 1
fi

# Verificar se venv está ativo
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Ambiente virtual não está ativo. Ativando..."
    if [ -d "venv" ]; then
        source venv/bin/activate
    else
        echo "❌ ERRO: Diretório venv não encontrado!"
        exit 1
    fi
fi

echo "✅ DATABASE_URL configurada"
echo "✅ Backup encontrado: backup_data.json"
echo "✅ Ambiente virtual ativo"
echo ""

# Confirmar com usuário
echo "⚠️  ATENÇÃO:"
echo "   Este script irá:"
echo "   1. Executar migrations no PostgreSQL"
echo "   2. Importar dados do backup_data.json"
echo ""
read -p "Deseja continuar? (s/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "❌ Importação cancelada."
    exit 0
fi

echo ""
echo "🔄 Executando migrations..."
python manage.py migrate

echo ""
echo "🔄 Importando dados..."
python manage.py loaddata backup_data.json

echo ""
echo "✅ Importação concluída com sucesso!"
echo ""
echo "📊 Verificar dados importados:"
echo "   python manage.py shell"
echo "   >>> from core.models import Usuario, Pedido"
echo "   >>> print(f'Usuários: {Usuario.objects.count()}')"
echo "   >>> print(f'Pedidos: {Pedido.objects.count()}')"
echo ""
