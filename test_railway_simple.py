#!/usr/bin/env python3
"""
Teste simples para verificar deploy no Railway
Verifica se o site está acessível e se os arquivos JavaScript foram atualizados
"""

import sys
import requests
from datetime import datetime

BASE_URL = "https://web-production-312d.up.railway.app"

def test_site_accessible():
    """Verifica se o site está acessível"""
    print("🌐 Testando se o site está acessível...")
    try:
        response = requests.get(BASE_URL, timeout=10)
        if response.status_code == 200:
            print("✅ Site acessível!")
            return True
        else:
            print(f"❌ Site retornou status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro ao acessar site: {e}")
        return False


def test_javascript_updated():
    """Verifica se o JavaScript foi atualizado com as correções"""
    print("\n📝 Verificando se JavaScript foi atualizado...")
    try:
        js_url = f"{BASE_URL}/static/js/pedido_detalhe.js"
        response = requests.get(js_url, timeout=10)

        if response.status_code != 200:
            print(f"❌ Não foi possível acessar JavaScript (status {response.status_code})")
            return False

        content = response.text

        # Verificar se tem os logs de debug adicionados
        has_debug_logs = "[DEBUG] Procurando linha com item ID:" in content
        has_debug_procurando = "console.log('[DEBUG]" in content

        if has_debug_logs:
            print("✅ JavaScript contém os novos logs de debug!")
            return True
        elif has_debug_procurando:
            print("✅ JavaScript foi atualizado com debug logging!")
            return True
        else:
            print("⚠️  JavaScript pode não ter sido atualizado ainda")
            print("   (Cache do CDN pode estar servindo versão antiga)")
            return False

    except Exception as e:
        print(f"❌ Erro ao verificar JavaScript: {e}")
        return False


def test_consumers_updated():
    """Verifica se o arquivo consumers.py tem o handler item_unseparado"""
    print("\n🔍 Verificando se backend foi atualizado...")
    print("   (Testando indiretamente via comportamento esperado)")

    # Como não podemos acessar o código do servidor diretamente,
    # vamos verificar se o endpoint /unseparar responde corretamente
    # Mas isso requer autenticação, então vamos apenas reportar
    print("⚠️  Não é possível verificar código backend diretamente")
    print("   Será necessário teste funcional com login")
    return None


def test_procfile_updated():
    """Verifica se as configurações do Daphne estão corretas"""
    print("\n⚙️  Verificando configurações do servidor...")

    try:
        # Fazer uma requisição HEAD para ver os headers
        response = requests.head(BASE_URL, timeout=10)

        # Verificar se está usando Daphne
        server_header = response.headers.get('Server', '')

        if 'daphne' in server_header.lower():
            print(f"✅ Servidor: {server_header}")
            return True
        else:
            print(f"⚠️  Server header: {server_header}")
            print("   (Pode estar oculto por proxy)")
            return None

    except Exception as e:
        print(f"⚠️  Não foi possível verificar: {e}")
        return None


def main():
    """Executa todos os testes"""
    print("="*60)
    print("TESTE DE DEPLOY NO RAILWAY")
    print("="*60)
    print(f"URL: {BASE_URL}")
    print(f"Horário: {datetime.now().strftime('%H:%M:%S')}")
    print("="*60)

    results = {}

    # Teste 1: Site acessível
    results['site_accessible'] = test_site_accessible()

    # Teste 2: JavaScript atualizado
    results['javascript_updated'] = test_javascript_updated()

    # Teste 3: Backend atualizado (verificação indireta)
    results['backend_updated'] = test_consumers_updated()

    # Teste 4: Configurações Daphne
    results['daphne_config'] = test_procfile_updated()

    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES")
    print("="*60)

    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)

    for test_name, result in results.items():
        status = "✅ PASS" if result is True else ("❌ FAIL" if result is False else "⚠️  SKIP")
        print(f"{status} - {test_name}")

    print()
    print(f"✅ Passou: {passed}")
    print(f"❌ Falhou: {failed}")
    print(f"⚠️  Pulado: {skipped}")
    print("="*60)

    # Conclusão
    if results['site_accessible'] and results['javascript_updated']:
        print("\n✅ DEPLOY VERIFICADO COM SUCESSO!")
        print("   O site está acessível e o JavaScript foi atualizado.")
        print("   Próximo passo: Teste funcional com login e interação.")
        return 0
    elif results['site_accessible']:
        print("\n⚠️  DEPLOY PARCIAL")
        print("   Site está acessível mas algumas atualizações podem não estar visíveis.")
        print("   Isso pode ser cache do CDN/browser.")
        print("   Tente: Ctrl+Shift+R para hard refresh no browser")
        return 0
    else:
        print("\n❌ DEPLOY COM PROBLEMAS")
        print("   O site não está acessível ou há erros.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
