#!/usr/bin/env python
"""
Script de teste para validar o sistema de bloqueio após 5 tentativas.
"""

import os
import django
import sys
from datetime import timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pmcell_settings.settings')
django.setup()

from django.test import Client
from django.utils import timezone
from apps.core.models import Usuario, LogAuditoria

def test_bloqueio():
    """Testa o bloqueio após 5 tentativas"""
    print("=" * 60)
    print("TESTE DE BLOQUEIO - FASE 2")
    print("=" * 60)

    # Pegar usuário e resetar tentativas
    user = Usuario.objects.get(numero_login=1000)
    user.tentativas_login = 0
    user.bloqueado_ate = None
    user.save()

    # Criar cliente
    client = Client()

    print("\n1. Testando 5 tentativas incorretas...")
    for i in range(1, 6):
        print(f"   Tentativa {i}...")
        response = client.post('/login/', {
            'numero_login': '1000',
            'pin': '9999'
        })

        user.refresh_from_db()

        if i < 5:
            if 'PIN incorreto' in response.content.decode():
                print(f"      ✓ Tentativa {i} rejeitada")
                print(f"      ✓ Tentativas registradas: {user.tentativas_login}")
            else:
                print(f"      ✗ Mensagem esperada não encontrada")
                return False
        else:
            # Quinta tentativa deve bloquear
            if 'bloqueado' in response.content.decode().lower():
                print(f"      ✓ Usuário bloqueado após 5 tentativas!")
                print(f"      ✓ Tentativas: {user.tentativas_login}")
                print(f"      ✓ Bloqueado até: {user.bloqueado_ate}")
            else:
                print(f"      ✗ Usuário não foi bloqueado")
                return False

    print("\n2. Testando login com usuário bloqueado...")
    response = client.post('/login/', {
        'numero_login': '1000',
        'pin': '1234'  # PIN correto, mas está bloqueado
    })

    if 'bloqueado' in response.content.decode().lower():
        print("   ✓ Login bloqueado corretamente")
    else:
        print("   ✗ Login não foi bloqueado")
        return False

    print("\n3. Testando desbloqueio automático (simular 30 minutos)...")
    # Simular que passou 30 minutos
    user.bloqueado_ate = timezone.now() - timedelta(minutes=1)  # 1 minuto no passado
    user.save()

    response = client.post('/login/', {
        'numero_login': '1000',
        'pin': '1234'
    }, follow=True)

    user.refresh_from_db()

    if response.status_code == 200 and user.bloqueado_ate is None:
        print("   ✓ Desbloqueio automático funcionou!")
        print("   ✓ Tentativas resetadas:", user.tentativas_login)
    else:
        print("   ✗ Desbloqueio automático não funcionou")
        return False

    print("\n4. Testando logs de auditoria...")
    log_bloqueio = LogAuditoria.objects.filter(
        usuario=user,
        acao='usuario_bloqueado'
    ).order_by('-timestamp').first()

    if log_bloqueio:
        print("   ✓ Log de bloqueio registrado")
        print(f"   ✓ Timestamp: {log_bloqueio.timestamp}")
    else:
        print("   ⚠ Log de bloqueio não encontrado")

    # Limpar
    user.tentativas_login = 0
    user.bloqueado_ate = None
    user.save()

    print("\n" + "=" * 60)
    print("✓ TODOS OS TESTES DE BLOQUEIO PASSARAM!")
    print("=" * 60)
    return True


if __name__ == '__main__':
    success = test_bloqueio()
    sys.exit(0 if success else 1)
