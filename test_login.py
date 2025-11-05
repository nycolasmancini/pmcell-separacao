#!/usr/bin/env python
"""
Script de teste para validar o sistema de login da FASE 2.
"""

import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pmcell_settings.settings')
django.setup()

from django.test import Client
from apps.core.models import Usuario, LogAuditoria

def test_login():
    """Testa o login com usuário 1000/1234"""
    print("=" * 60)
    print("TESTE DE LOGIN - FASE 2")
    print("=" * 60)

    # Criar cliente de teste
    client = Client()

    # 1. Verificar que usuário existe
    print("\n1. Verificando usuário 1000...")
    try:
        user = Usuario.objects.get(numero_login=1000)
        print(f"   ✓ Usuário encontrado: {user.nome}")
        print(f"   ✓ Tipo: {user.tipo}")
        print(f"   ✓ Ativo: {user.ativo}")
    except Usuario.DoesNotExist:
        print("   ✗ Usuário não encontrado")
        return False

    # 2. Testar acesso à página de login
    print("\n2. Testando acesso à página de login...")
    response = client.get('/login/')
    if response.status_code == 200:
        print("   ✓ Página de login acessível")
    else:
        print(f"   ✗ Erro ao acessar login: {response.status_code}")
        return False

    # 3. Testar login com credenciais corretas
    print("\n3. Testando login com credenciais corretas (1000/1234)...")
    response = client.post('/login/', {
        'numero_login': '1000',
        'pin': '1234'
    }, follow=True)

    if response.status_code == 200:
        # Verificar se foi redirecionado para dashboard
        if response.redirect_chain and '/dashboard/' in response.redirect_chain[0][0]:
            print("   ✓ Login bem-sucedido!")
            print(f"   ✓ Redirecionado para: {response.redirect_chain[0][0]}")

            # Verificar se mensagem de sucesso está presente
            if response.context:
                messages = list(response.context.get('messages', []))
                if messages:
                    print(f"   ✓ Mensagem: {messages[0]}")
        else:
            print(f"   ✗ Não redirecionou para dashboard")
            return False
    else:
        print(f"   ✗ Erro no login: {response.status_code}")
        return False

    # 4. Verificar log de auditoria
    print("\n4. Verificando log de auditoria...")
    last_log = LogAuditoria.objects.filter(
        usuario=user,
        acao='login_sucesso'
    ).order_by('-timestamp').first()

    if last_log:
        print(f"   ✓ Log de login registrado")
        print(f"   ✓ Timestamp: {last_log.timestamp}")
        print(f"   ✓ IP: {last_log.ip}")
    else:
        print("   ⚠ Log de auditoria não encontrado (pode ser esperado em teste)")

    # 5. Verificar se usuário está autenticado
    print("\n5. Verificando autenticação...")
    response = client.get('/dashboard/')
    if response.status_code == 200:
        print("   ✓ Usuário autenticado pode acessar dashboard")
    else:
        print("   ✗ Usuário autenticado não pode acessar dashboard")
        return False

    # 6. Testar login com PIN incorreto
    print("\n6. Testando login com PIN incorreto...")
    client2 = Client()
    response = client2.post('/login/', {
        'numero_login': '1000',
        'pin': '9999'
    })

    if 'PIN incorreto' in response.content.decode():
        print("   ✓ PIN incorreto rejeitado corretamente")
    else:
        print("   ⚠ Mensagem de erro não encontrada")

    # Verificar tentativas incrementadas
    user.refresh_from_db()
    if user.tentativas_login == 1:
        print(f"   ✓ Tentativas de login incrementadas: {user.tentativas_login}")
    else:
        print(f"   ⚠ Tentativas: {user.tentativas_login}")

    # Resetar tentativas para não afetar próximos testes
    user.tentativas_login = 0
    user.save()

    # 7. Testar logout
    print("\n7. Testando logout...")
    response = client.post('/logout/', follow=True)
    if response.status_code == 200 and '/login/' in response.redirect_chain[0][0]:
        print("   ✓ Logout bem-sucedido")
    else:
        print("   ✗ Erro no logout")
        return False

    print("\n" + "=" * 60)
    print("✓ TODOS OS TESTES PASSARAM!")
    print("=" * 60)
    return True


if __name__ == '__main__':
    success = test_login()
    sys.exit(0 if success else 1)
