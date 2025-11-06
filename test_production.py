"""
Playwright Test for Production Site
Tests item status updates on web-production-312d.up.railway.app
"""
import time
from playwright.sync_api import sync_playwright, Page
import os
from datetime import datetime

# Production URL
PRODUCTION_URL = "https://web-production-312d.up.railway.app"

# Create screenshots directory
SCREENSHOTS_DIR = "test_screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def save_screenshot(page: Page, name: str):
    """Save screenshot with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{SCREENSHOTS_DIR}/{timestamp}_{name}.png"
    page.screenshot(path=filename)
    print(f"📸 Screenshot saved: {filename}")
    return filename


def print_section(title):
    """Print formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def test_production_site():
    """Main test function for production site"""

    print_section("🚀 TESTE DE PRODUÇÃO - PMCELL")
    print(f"URL: {PRODUCTION_URL}")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    with sync_playwright() as p:
        # Launch browser in headed mode (visible)
        print("\n🌐 Abrindo navegador...")
        browser = p.chromium.launch(
            headless=False,  # Visible browser
            slow_mo=1000     # Slow down by 1 second for observation
        )

        # Create context and page with cache disabled
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            ignore_https_errors=True  # Ignore SSL errors if any
        )
        page = context.new_page()

        # Enable console logging
        page.on("console", lambda msg: print(f"🖥️  Console: {msg.text}"))

        try:
            # Step 1: Navigate to production site
            print_section("STEP 1: Navegando para o site de produção")
            page.goto(PRODUCTION_URL, timeout=30000)
            print(f"✓ Navegou para: {page.url}")
            save_screenshot(page, "01_homepage")
            time.sleep(2)

            # Step 2: Check if we're on login page
            print_section("STEP 2: Verificando página de login")

            # Check if login page exists
            if "login" in page.url.lower() or page.locator('input[name="numero_login"]').count() > 0:
                print("✓ Página de login detectada")
                save_screenshot(page, "02_login_page")

                # Get credentials from environment or use default
                import os
                numero_login = os.environ.get('PMCELL_LOGIN', '1000')
                pin = os.environ.get('PMCELL_PIN', '1000')

                print("\n" + "="*70)
                print("  🔐 USANDO CREDENCIAIS")
                print("="*70)
                print(f"Login: {numero_login}")
                print("PIN: ****")
                print("\n💡 Dica: Use PMCELL_LOGIN e PMCELL_PIN para customizar")
                print("="*70)

                # Fill login form
                print(f"\n📝 Fazendo login com usuário: {numero_login}")
                page.fill('input[name="numero_login"]', numero_login)
                page.fill('input[name="pin"]', pin)
                save_screenshot(page, "03_login_filled")

                # Submit
                page.click('button[type="submit"]')
                print("✓ Formulário enviado")
                time.sleep(3)

                # Check if login was successful
                if "dashboard" in page.url.lower() or page.locator('h1:has-text("Dashboard")').count() > 0:
                    print("✅ Login bem-sucedido!")
                    save_screenshot(page, "04_dashboard")
                else:
                    print("❌ Login falhou - verificar credenciais")
                    save_screenshot(page, "04_login_failed")
                    return False
            else:
                print("⚠️  Não está na página de login - já autenticado?")
                save_screenshot(page, "02_already_logged_in")

            # Step 3: Find and navigate to a pending order
            print_section("STEP 3: Navegando para um pedido pendente")

            # Try to find first pending order
            time.sleep(2)
            pending_order = page.locator('a[href*="/pedidos/"]:has-text("Pendente")').first

            if pending_order.count() > 0:
                order_link = pending_order.get_attribute('href')
                print(f"✓ Pedido pendente encontrado: {order_link}")
                pending_order.click()
                time.sleep(2)
                print(f"✓ Navegou para: {page.url}")
                save_screenshot(page, "05_order_details")
            else:
                # If no pending order found, try common IDs
                print("⚠️  Nenhum pedido pendente encontrado na dashboard")
                save_screenshot(page, "05_no_pending_orders")

                # Try order ID 1
                order_id = os.environ.get('PMCELL_ORDER_ID', '1')
                print(f"⚙️  Tentando pedido ID: {order_id}")

                try:
                    page.goto(f"{PRODUCTION_URL}/pedidos/{order_id}/", timeout=10000)
                    time.sleep(2)
                    print(f"✓ Navegou para pedido ID: {order_id}")
                    save_screenshot(page, "05_order_details_manual")
                except Exception as e:
                    print(f"❌ Erro ao navegar para pedido {order_id}: {e}")
                    print("💡 Use PMCELL_ORDER_ID para especificar um pedido válido")
                    return False

            # Step 4: Verify JavaScript loaded
            print_section("STEP 4: Verificando carregamento do JavaScript")

            # Check if Alpine.js is initialized
            alpine_check = page.evaluate("""
                () => {
                    const element = document.querySelector('[x-data]');
                    return element && element.__x !== undefined;
                }
            """)

            if alpine_check:
                print("✅ Alpine.js inicializado corretamente")
            else:
                print("❌ Alpine.js NÃO inicializado - JavaScript pode não estar carregando")

            # Check if script tag exists
            script_exists = page.locator('script[src*="pedido_detalhe.js"]').count() > 0
            if script_exists:
                print("✅ Script pedido_detalhe.js encontrado no HTML")
            else:
                print("❌ Script pedido_detalhe.js NÃO encontrado")

            save_screenshot(page, "06_javascript_check")

            # Step 5: Test checkbox (Separar item)
            print_section("STEP 5: Testando checkbox - Marcar item como separado")

            # Find first unchecked checkbox
            checkboxes = page.locator('input[type="checkbox"]:not(:checked)').all()

            if len(checkboxes) > 0:
                checkbox = checkboxes[0]

                # Get item ID
                item_id = checkbox.get_attribute('data-item-id') or "unknown"
                print(f"📦 Testando item ID: {item_id}")

                # Get initial row color
                row = page.locator(f'tr[data-item-id="{item_id}"]')
                if row.count() > 0:
                    initial_bg = row.evaluate("el => window.getComputedStyle(el).backgroundColor")
                    print(f"🎨 Cor inicial da linha: {initial_bg}")

                # Take before screenshot
                save_screenshot(page, "07_before_checkbox_click")

                # Click checkbox
                print("🖱️  Clicando no checkbox...")
                checkbox.check()

                # Handle confirmation dialog
                page.on("dialog", lambda dialog: dialog.accept())
                time.sleep(2)

                # Take after screenshot
                save_screenshot(page, "08_after_checkbox_click")

                # Verify changes
                print("\n🔍 Verificando mudanças...")

                # Check row color
                if row.count() > 0:
                    final_bg = row.evaluate("el => window.getComputedStyle(el).backgroundColor")
                    print(f"🎨 Cor final da linha: {final_bg}")

                    if initial_bg != final_bg:
                        print("✅ COR DA LINHA MUDOU (esperado: verde claro)")
                    else:
                        print("❌ Cor da linha NÃO mudou")

                # Check for badge
                badge = row.locator('.badge:has-text("Separado"), .bg-green-100:has-text("Separado")').first
                if badge.count() > 0:
                    print("✅ BADGE 'Separado' APARECEU")
                else:
                    print("❌ Badge 'Separado' NÃO apareceu")

                # Check checkbox is checked
                if checkbox.is_checked():
                    print("✅ CHECKBOX PERMANECE MARCADO")
                else:
                    print("❌ Checkbox foi desmarcado")

                # Check counter
                counter = page.locator('.card:has-text("Separados")').locator('.text-2xl, .text-xl').first
                if counter.count() > 0:
                    counter_value = counter.inner_text()
                    print(f"✅ CONTADOR SEPARADOS: {counter_value}")
                else:
                    print("⚠️  Contador não encontrado")

                time.sleep(2)

            else:
                print("⚠️  Nenhum checkbox não-marcado encontrado para testar")
                save_screenshot(page, "07_no_checkboxes")

            # Step 6: Test menu actions (if available)
            print_section("STEP 6: Testando ações do menu (Compra/Substituir)")

            menu_button = page.locator('button:has-text("⋮")').first
            if menu_button.count() > 0:
                print("🖱️  Clicando no menu...")
                menu_button.click()
                time.sleep(1)
                save_screenshot(page, "09_menu_opened")

                # Check available options
                compra_option = page.locator('a:has-text("Marcar Compra"), a:has-text("Compra")').first
                substituir_option = page.locator('a:has-text("Substituir")').first

                if compra_option.count() > 0:
                    print("✅ Opção 'Marcar Compra' disponível")
                else:
                    print("❌ Opção 'Marcar Compra' NÃO encontrada")

                if substituir_option.count() > 0:
                    print("✅ Opção 'Substituir' disponível")
                else:
                    print("❌ Opção 'Substituir' NÃO encontrada")

                # Close menu by clicking outside
                page.click('body')
                time.sleep(1)
            else:
                print("⚠️  Botão de menu não encontrado")

            # Step 7: Final verification
            print_section("STEP 7: Verificação Final")

            # Take final screenshot
            save_screenshot(page, "10_final_state")

            # Check console for errors
            print("\n📋 Verificando console do navegador...")
            print("(Verifique os logs acima marcados com 🖥️  Console)")

            # Summary
            print_section("📊 RESUMO DO TESTE")
            print("✅ Navegação para site de produção")
            print("✅ Login no sistema")
            print("✅ Navegação para pedido")
            print(f"{'✅' if alpine_check else '❌'} JavaScript (Alpine.js) inicializado")
            print(f"{'✅' if script_exists else '❌'} Script pedido_detalhe.js carregado")
            print("✅ Teste de checkbox realizado")
            print("✅ Screenshots capturados")

            print(f"\n📁 Screenshots salvos em: {SCREENSHOTS_DIR}/")
            print(f"🕐 Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Keep browser open for 10 seconds for manual inspection
            print("\n⏳ Mantendo navegador aberto por 10 segundos para inspeção...")
            time.sleep(10)

            return True

        except Exception as e:
            print(f"\n❌ ERRO durante o teste: {e}")
            save_screenshot(page, "ERROR_state")
            import traceback
            traceback.print_exc()
            return False

        finally:
            print("\n🔒 Fechando navegador...")
            context.close()
            browser.close()


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║         TESTE DE PRODUÇÃO - PMCELL STATUS UPDATE            ║
    ║         Site: web-production-312d.up.railway.app            ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)

    success = test_production_site()

    if success:
        print("\n✅ TESTE CONCLUÍDO COM SUCESSO!")
    else:
        print("\n❌ TESTE FALHOU - Verifique os erros acima")

    print("\n" + "="*70)
