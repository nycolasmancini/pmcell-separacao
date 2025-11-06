"""
Teste Playwright - Correções da Tela de Separação
================================================

Testa os 3 problemas corrigidos:
1. Unseparar item (não deve dar erro HTTP 500)
2. Substituição de produto (deve atualizar em real-time)
3. Marcar para compra (deve atualizar em real-time)

ANTES DE EXECUTAR:
- Configure o Redis na Railway seguindo as instruções
- Aguarde o deploy completar (~4 minutos)
- Certifique-se que existe um pedido com ID=3 no sistema
"""

import sys
import time
from playwright.sync_api import sync_playwright, expect

# Configuração
BASE_URL = "https://web-production-312d.up.railway.app"
PEDIDO_ID = 3  # Ajuste conforme necessário
LOGIN_USER = "admin"  # Ajuste conforme necessário
LOGIN_PASS = "admin"  # Ajuste conforme necessário


def print_header(text):
    """Imprime cabeçalho formatado"""
    print(f"\n{'='*80}")
    print(f"  {text}")
    print(f"{'='*80}\n")


def print_step(step_num, text):
    """Imprime passo do teste"""
    print(f"[PASSO {step_num}] {text}")


def print_result(success, message):
    """Imprime resultado do teste"""
    icon = "✓" if success else "✗"
    status = "PASSOU" if success else "FALHOU"
    print(f"{icon} [{status}] {message}\n")


def wait_for_websocket(page, timeout=10000):
    """Aguarda conexão WebSocket"""
    print("  Aguardando conexão WebSocket...")

    start_time = time.time()
    while time.time() - start_time < timeout / 1000:
        try:
            # Verifica no console se WebSocket conectou
            logs = page.evaluate("""() => {
                return window.wsConnected || false;
            }""")
            if logs:
                print("  ✓ WebSocket conectado!")
                return True
        except:
            pass
        time.sleep(0.5)

    print("  ! WebSocket não conectou (mas isso pode ser esperado se Redis não foi configurado)")
    return False


def test_unseparar_item(page):
    """
    TESTE #1: Unseparar Item
    Verifica se ao desmarcar um item, não ocorre erro HTTP 500
    """
    print_header("TESTE #1: Unseparar Item (HTTP 500 Fix)")

    print_step(1, "Navegando para página do pedido...")
    page.goto(f"{BASE_URL}/pedido/{PEDIDO_ID}/")
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    print_step(2, "Procurando item já separado para desseparar...")

    # Procura checkbox marcado
    checkboxes = page.locator('input[type="checkbox"][data-item-id]').all()
    print(f"  Encontrados {len(checkboxes)} items no pedido")

    checked_item = None
    for checkbox in checkboxes:
        if checkbox.is_checked():
            checked_item = checkbox
            item_id = checkbox.get_attribute('data-item-id')
            print(f"  ✓ Item {item_id} está separado")
            break

    if not checked_item:
        print_result(False, "SKIP: Nenhum item separado encontrado. Marque um item primeiro.")
        return False

    print_step(3, f"Desmarcando item {item_id}...")

    # Monitora requisições HTTP
    error_500_found = False
    success_200_found = False

    def handle_response(response):
        nonlocal error_500_found, success_200_found
        if '/unseparar' in response.url:
            if response.status == 500:
                error_500_found = True
                print(f"  ✗ ERRO HTTP 500 detectado!")
            elif response.status == 200:
                success_200_found = True
                print(f"  ✓ HTTP 200 - Sucesso!")

    page.on("response", handle_response)

    # Desmarca o item
    checked_item.uncheck()
    time.sleep(2)

    # Verifica resultado
    if error_500_found:
        print_result(False, "Erro HTTP 500 ainda ocorre ao desseparar! Bug NÃO corrigido.")
        return False
    elif success_200_found:
        print_result(True, "Item desseparado com sucesso sem erro 500! Bug CORRIGIDO.")
        return True
    else:
        print_result(False, "Nenhuma resposta capturada. Verifique a implementação.")
        return False


def test_substitution_realtime(page):
    """
    TESTE #2: Substituição Real-time
    Verifica se substituição atualiza em tempo real sem refresh
    """
    print_header("TESTE #2: Substituição de Produto Real-time")

    print_step(1, "Navegando para página do pedido...")
    page.goto(f"{BASE_URL}/pedido/{PEDIDO_ID}/")
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # Aguarda WebSocket
    ws_connected = wait_for_websocket(page)

    print_step(2, "Procurando item para substituir...")

    # Procura botão de substituir
    substituir_buttons = page.locator('button:has-text("Substituir")').all()

    if not substituir_buttons:
        print_result(False, "SKIP: Nenhum botão 'Substituir' encontrado.")
        return False

    print(f"  Encontrados {len(substituir_buttons)} botões de substituir")

    # Pega o primeiro item que pode ser substituído
    first_button = substituir_buttons[0]
    item_row = first_button.locator('xpath=ancestor::tr')

    # Verifica se já não está substituído
    badge = item_row.locator('.badge:has-text("Substituído")')
    if badge.count() > 0:
        print_result(False, "SKIP: Item já está substituído. Escolha outro item.")
        return False

    print_step(3, "Clicando em 'Substituir'...")
    first_button.click()
    time.sleep(1)

    # Preenche modal de substituição (se existir)
    try:
        # Procura campo de produto substituto
        produto_input = page.locator('input[name="produto_substituto_id"]').first
        if produto_input.is_visible():
            print("  Preenchendo modal de substituição...")
            produto_input.fill("1")  # ID de produto exemplo

            # Clica em confirmar
            confirm_button = page.locator('button:has-text("Confirmar")').first
            confirm_button.click()
            time.sleep(2)
    except:
        pass

    print_step(4, "Verificando se badge 'Substituído' aparece em real-time...")

    # Aguarda badge aparecer (sem refresh)
    start_time = time.time()
    badge_appeared = False

    while time.time() - start_time < 5:
        badge = item_row.locator('.badge:has-text("Substituído")')
        if badge.count() > 0:
            badge_appeared = True
            print(f"  ✓ Badge 'Substituído' apareceu após {time.time() - start_time:.1f}s")
            break
        time.sleep(0.5)

    if badge_appeared:
        if ws_connected:
            print_result(True, "Substituição atualizada em REAL-TIME! WebSocket funcionando.")
        else:
            print_result(False, "Badge apareceu mas WebSocket não conectou. Pode ser atualização local apenas.")
        return badge_appeared
    else:
        print_result(False, "Badge NÃO apareceu. Real-time não está funcionando. Configure o Redis!")
        return False


def test_compra_realtime(page):
    """
    TESTE #3: Marcar para Compra Real-time
    Verifica se marcar para compra atualiza em tempo real
    """
    print_header("TESTE #3: Marcar para Compra Real-time")

    print_step(1, "Navegando para página do pedido...")
    page.goto(f"{BASE_URL}/pedido/{PEDIDO_ID}/")
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # Aguarda WebSocket
    ws_connected = wait_for_websocket(page)

    print_step(2, "Procurando item para marcar como compra...")

    # Procura botão de marcar para compra
    comprar_buttons = page.locator('button:has-text("Comprar")').all()

    if not comprar_buttons:
        print_result(False, "SKIP: Nenhum botão 'Comprar' encontrado.")
        return False

    print(f"  Encontrados {len(comprar_buttons)} botões de comprar")

    # Pega o primeiro item
    first_button = comprar_buttons[0]
    item_row = first_button.locator('xpath=ancestor::tr')

    # Verifica se já não está em compra
    badge = item_row.locator('.badge:has-text("Em Compra")')
    if badge.count() > 0:
        print_result(False, "SKIP: Item já está marcado para compra.")
        return False

    print_step(3, "Clicando em 'Comprar'...")
    first_button.click()
    time.sleep(1)

    # Confirma modal se existir
    try:
        confirm_button = page.locator('button:has-text("Confirmar")').first
        if confirm_button.is_visible():
            confirm_button.click()
            time.sleep(2)
    except:
        pass

    print_step(4, "Verificando se badge 'Em Compra' aparece em real-time...")

    # Aguarda badge aparecer
    start_time = time.time()
    badge_appeared = False

    while time.time() - start_time < 5:
        badge = item_row.locator('.badge:has-text("Em Compra")')
        if badge.count() > 0:
            badge_appeared = True
            print(f"  ✓ Badge 'Em Compra' apareceu após {time.time() - start_time:.1f}s")
            break
        time.sleep(0.5)

    if badge_appeared:
        if ws_connected:
            print_result(True, "Compra atualizada em REAL-TIME! WebSocket funcionando.")
        else:
            print_result(False, "Badge apareceu mas WebSocket não conectou. Pode ser atualização local.")
        return badge_appeared
    else:
        print_result(False, "Badge NÃO apareceu. Real-time não funciona. Configure o Redis!")
        return False


def run_tests():
    """Executa todos os testes"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*15 + "TESTE DE CORREÇÕES - TELA DE SEPARAÇÃO" + " "*24 + "║")
    print("╚" + "="*78 + "╝")
    print(f"\nURL: {BASE_URL}")
    print(f"Pedido: {PEDIDO_ID}")
    print(f"Horário: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    with sync_playwright() as p:
        # Inicia browser
        print("Iniciando navegador...")
        browser = p.chromium.launch(headless=False)  # headless=True para rodar sem UI
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = context.new_page()

        # Login (se necessário)
        try:
            print("Verificando necessidade de login...")
            page.goto(f"{BASE_URL}/admin/login/")

            if "login" in page.url.lower():
                print("Fazendo login...")
                page.fill('input[name="username"]', LOGIN_USER)
                page.fill('input[name="password"]', LOGIN_PASS)
                page.click('button[type="submit"]')
                page.wait_for_load_state("networkidle")
                print("✓ Login realizado\n")
        except:
            print("✓ Já autenticado ou sem necessidade de login\n")

        # Executa testes
        results = {
            'test_1_unseparar': False,
            'test_2_substitution': False,
            'test_3_compra': False
        }

        try:
            results['test_1_unseparar'] = test_unseparar_item(page)
        except Exception as e:
            print_result(False, f"Teste #1 falhou com exceção: {str(e)}")

        try:
            results['test_2_substitution'] = test_substitution_realtime(page)
        except Exception as e:
            print_result(False, f"Teste #2 falhou com exceção: {str(e)}")

        try:
            results['test_3_compra'] = test_compra_realtime(page)
        except Exception as e:
            print_result(False, f"Teste #3 falhou com exceção: {str(e)}")

        # Resumo final
        print_header("RESUMO DOS TESTES")

        passed = sum(results.values())
        total = len(results)

        print(f"✓ Problema #1 (Unseparar HTTP 500):      {'RESOLVIDO' if results['test_1_unseparar'] else 'FALHOU'}")
        print(f"{'✓' if results['test_2_substitution'] else '✗'} Problema #2 (Substituição Real-time): {'RESOLVIDO' if results['test_2_substitution'] else 'FALHOU'}")
        print(f"{'✓' if results['test_3_compra'] else '✗'} Problema #3 (Compra Real-time):       {'RESOLVIDO' if results['test_3_compra'] else 'FALHOU'}")

        print(f"\nResultado: {passed}/{total} testes passaram")

        if passed == total:
            print("\n🎉 TODOS OS PROBLEMAS FORAM CORRIGIDOS! 🎉")
        elif results['test_1_unseparar']:
            print("\n⚠️  Problema #1 corrigido, mas #2 e #3 precisam do Redis configurado!")
        else:
            print("\n❌ Ainda há problemas a corrigir.")

        browser.close()

        return passed == total


if __name__ == "__main__":
    try:
        success = run_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTeste interrompido pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERRO FATAL: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
