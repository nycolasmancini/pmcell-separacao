"""
Playwright E2E Tests for Order Separation UX Improvements
Tests the new checkbox behavior without confirmation dialogs and unseparate functionality
"""
import pytest
from playwright.sync_api import Page, expect, Browser
import time
from django.test import LiveServerTestCase
from apps.core.models import Usuario, Pedido, ItemPedido, Produto


class TestSeparationUXImprovements(LiveServerTestCase):
    """
    End-to-end tests for improved order separation UX
    - No confirmation dialog when checking items
    - Ability to uncheck separated items (unseparate)
    - Cannot uncheck substituted items
    - Items em_compra transition correctly to separated
    """

    @classmethod
    def setUpClass(cls):
        """Set up test data once for all tests"""
        super().setUpClass()

        # Create test user (SEPARADOR)
        cls.test_user = Usuario.objects.create_user(
            numero_login=1234,
            nome='Test Separador',
            tipo='SEPARADOR',
            pin='1234'
        )

        # Create compradora user for purchase tests
        cls.compradora_user = Usuario.objects.create_user(
            numero_login=5678,
            nome='Test Compradora',
            tipo='COMPRADORA',
            pin='5678'
        )

        # Create test products
        cls.product1 = Produto.objects.create(
            codigo='TEST001',
            descricao='Test Product 1',
            preco=10.00,
            estoque_atual=100
        )

        cls.product2 = Produto.objects.create(
            codigo='TEST002',
            descricao='Test Product 2',
            preco=20.00,
            estoque_atual=50
        )

        cls.product3 = Produto.objects.create(
            codigo='TEST003',
            descricao='Test Product 3 for Substitution',
            preco=30.00,
            estoque_atual=0
        )

    def setUp(self):
        """Set up test data for each test"""
        # Create a test order (pedido) with items
        self.pedido = Pedido.objects.create(
            numero_orcamento='TEST-001',
            cliente='Test Client',
            vendedor='Test Seller',
            valor_total=60.00,
            status='PENDENTE'
        )

        # Create test items
        self.item1 = ItemPedido.objects.create(
            pedido=self.pedido,
            produto=self.product1,
            quantidade_solicitada=1,
            preco_unitario=10.00
        )

        self.item2 = ItemPedido.objects.create(
            pedido=self.pedido,
            produto=self.product2,
            quantidade_solicitada=2,
            preco_unitario=20.00
        )

        self.item3 = ItemPedido.objects.create(
            pedido=self.pedido,
            produto=self.product3,
            quantidade_solicitada=1,
            preco_unitario=30.00
        )

    def login(self, page: Page, numero_login: int = 1234, pin: str = '1234'):
        """Helper method to login"""
        page.goto(f'{self.live_server_url}/login/')
        page.fill('input[name="numero_login"]', str(numero_login))
        page.fill('input[name="pin"]', pin)
        page.click('button[type="submit"]')
        page.wait_for_url(f'{self.live_server_url}/dashboard/')

    def navigate_to_pedido_detalhe(self, page: Page):
        """Helper method to navigate to pedido detail page"""
        page.goto(f'{self.live_server_url}/pedidos/{self.pedido.id}/')
        page.wait_for_load_state('networkidle')

    @pytest.mark.django_db
    def test_checkbox_no_confirmation_dialog(self, page: Page):
        """
        Test 1: Verify that checking a checkbox does NOT show a confirmation dialog
        """
        self.login(page)
        self.navigate_to_pedido_detalhe(page)

        # Setup dialog listener to detect if any confirmation appears
        dialog_appeared = []

        def handle_dialog(dialog):
            dialog_appeared.append(True)
            dialog.accept()

        page.on("dialog", handle_dialog)

        # Find and check the first item's checkbox
        checkbox = page.locator(f'.item-checkbox[data-item-id="{self.item1.id}"]')
        checkbox.check()

        # Wait a moment for any potential dialog
        time.sleep(0.5)

        # Verify no dialog appeared
        assert len(dialog_appeared) == 0, "Confirmation dialog should NOT appear when checking checkbox"

        # Verify item is marked as separated in UI
        row = page.locator(f'tr[data-item-id="{self.item1.id}"]')
        expect(row).to_have_class('row-separated')

        # Verify checkbox is checked
        expect(checkbox).to_be_checked()

        # Verify status badge shows "Separado"
        status_badge = row.locator('.status-badge .status-text')
        expect(status_badge).to_have_text('✓ Separado')

    @pytest.mark.django_db
    def test_uncheck_separated_item_removes_separation(self, page: Page):
        """
        Test 2: Verify that unchecking a separated item removes the separation
        """
        # First, mark item as separated
        self.item1.separado = True
        self.item1.separado_por = self.test_user
        from django.utils import timezone
        self.item1.separado_em = timezone.now()
        self.item1.save()

        self.login(page)
        self.navigate_to_pedido_detalhe(page)

        # Verify item shows as separated
        checkbox = page.locator(f'.item-checkbox[data-item-id="{self.item1.id}"]')
        expect(checkbox).to_be_checked()

        row = page.locator(f'tr[data-item-id="{self.item1.id}"]')
        expect(row).to_have_class('row-separated')

        # Uncheck the checkbox
        checkbox.uncheck()

        # Wait for server response
        time.sleep(0.5)

        # Verify checkbox is unchecked
        expect(checkbox).not_to_be_checked()

        # Verify visual feedback is removed
        expect(row).not_to_have_class('row-separated')

        # Verify status badge shows "Pendente"
        status_badge = row.locator('.status-badge .status-text')
        expect(status_badge).to_have_text('⏳ Pendente')

        # Verify in database
        self.item1.refresh_from_db()
        assert self.item1.separado == False, "Item should be marked as NOT separated in database"
        assert self.item1.separado_por is None, "separado_por should be cleared"
        assert self.item1.separado_em is None, "separado_em should be cleared"

    @pytest.mark.django_db
    def test_cannot_uncheck_substituted_item(self, page: Page):
        """
        Test 3: Verify that substituted items CANNOT be unchecked
        """
        # Mark item as both separated AND substituted
        from django.utils import timezone
        self.item3.separado = True
        self.item3.separado_por = self.test_user
        self.item3.separado_em = timezone.now()
        self.item3.substituido = True
        self.item3.produto_substituto = 'TEST-SUB-001'
        self.item3.save()

        self.login(page)
        self.navigate_to_pedido_detalhe(page)

        # Verify item shows as separated
        checkbox = page.locator(f'.item-checkbox[data-item-id="{self.item3.id}"]')
        expect(checkbox).to_be_checked()

        # Try to uncheck the checkbox
        checkbox.uncheck()

        # Wait for server response
        time.sleep(0.5)

        # Verify checkbox is STILL checked (server rejected the unseparate request)
        expect(checkbox).to_be_checked()

        # Verify item is still separated in database
        self.item3.refresh_from_db()
        assert self.item3.separado == True, "Substituted item should remain separated"
        assert self.item3.substituido == True, "Item should still be marked as substituted"

    @pytest.mark.django_db
    def test_em_compra_item_transitions_to_separated(self, page: Page):
        """
        Test 4: Verify that items marked 'em_compra' can be directly marked as separated
        According to user requirement: "se um produto estiver em compra, seu checkbox nao deve estar marcado.
        Caso clique no checkbox, ele irá de compras para separado diretamente"
        """
        # Mark item as em_compra
        from django.utils import timezone
        self.item2.em_compra = True
        self.item2.marcado_compra_por = self.compradora_user
        self.item2.marcado_compra_em = timezone.now()
        self.item2.save()

        self.login(page)
        self.navigate_to_pedido_detalhe(page)

        # Verify checkbox is UNCHECKED (item em_compra should show unchecked)
        checkbox = page.locator(f'.item-checkbox[data-item-id="{self.item2.id}"]')
        expect(checkbox).not_to_be_checked()

        # Verify status badge shows "Em Compra"
        row = page.locator(f'tr[data-item-id="{self.item2.id}"]')
        status_badge = row.locator('.status-badge .status-text')
        expect(status_badge).to_contain_text('Compra')

        # Check the checkbox (should transition from em_compra to separado)
        checkbox.check()

        # Wait for server response
        time.sleep(0.5)

        # Verify checkbox is checked
        expect(checkbox).to_be_checked()

        # Verify visual feedback shows separated
        expect(row).to_have_class('row-separated')

        # Verify status badge shows "Separado"
        expect(status_badge).to_have_text('✓ Separado')

        # Verify in database
        self.item2.refresh_from_db()
        assert self.item2.separado == True, "Item should be marked as separated"
        assert self.item2.em_compra == False, "em_compra should be set to False"
        assert self.item2.separado_por == self.test_user, "Should be separated by current user"

    @pytest.mark.django_db
    def test_visual_feedback_removed_on_unseparate(self, page: Page):
        """
        Test 5: Verify all visual feedback is properly removed when unseparating an item
        """
        # Mark item as separated
        from django.utils import timezone
        self.item1.separado = True
        self.item1.separado_por = self.test_user
        self.item1.separado_em = timezone.now()
        self.item1.save()

        self.login(page)
        self.navigate_to_pedido_detalhe(page)

        row = page.locator(f'tr[data-item-id="{self.item1.id}"]')

        # Verify separated visual state
        expect(row).to_have_class('row-separated')
        description = row.locator('.item-description')
        expect(description).to_have_class('line-through')

        # Uncheck the checkbox
        checkbox = page.locator(f'.item-checkbox[data-item-id="{self.item1.id}"]')
        checkbox.uncheck()

        # Wait for server response
        time.sleep(0.5)

        # Verify all visual feedback is removed
        expect(row).not_to_have_class('row-separated')
        expect(description).not_to_have_class('line-through')

        # Verify status badge reset to Pendente
        status_badge = row.locator('.status-badge')
        expect(status_badge).to_have_class('bg-gray-100')
        expect(status_badge).to_have_class('text-gray-800')

    @pytest.mark.django_db
    def test_multiple_items_check_uncheck_sequence(self, page: Page):
        """
        Test 6: Verify checking and unchecking multiple items works correctly
        """
        self.login(page)
        self.navigate_to_pedido_detalhe(page)

        # Check item 1
        checkbox1 = page.locator(f'.item-checkbox[data-item-id="{self.item1.id}"]')
        checkbox1.check()
        time.sleep(0.3)

        # Check item 2
        checkbox2 = page.locator(f'.item-checkbox[data-item-id="{self.item2.id}"]')
        checkbox2.check()
        time.sleep(0.3)

        # Verify both are checked
        expect(checkbox1).to_be_checked()
        expect(checkbox2).to_be_checked()

        # Uncheck item 1
        checkbox1.uncheck()
        time.sleep(0.3)

        # Verify states
        expect(checkbox1).not_to_be_checked()
        expect(checkbox2).to_be_checked()

        # Verify database states
        self.item1.refresh_from_db()
        self.item2.refresh_from_db()
        assert self.item1.separado == False, "Item 1 should be unseparated"
        assert self.item2.separado == True, "Item 2 should remain separated"

    @pytest.mark.django_db
    def test_websocket_broadcasts_unseparate_action(self, page: Page, context):
        """
        Test 7: Verify WebSocket broadcasts unseparate action to other connected users
        """
        # Mark item as separated
        from django.utils import timezone
        self.item1.separado = True
        self.item1.separado_por = self.test_user
        self.item1.separado_em = timezone.now()
        self.item1.save()

        # Login in first browser
        self.login(page)
        self.navigate_to_pedido_detalhe(page)

        # Open second browser context (simulating another user)
        page2 = context.new_page()
        self.login(page2)
        page2.goto(f'{self.live_server_url}/pedidos/{self.pedido.id}/')
        page2.wait_for_load_state('networkidle')

        # Uncheck in first browser
        checkbox1 = page.locator(f'.item-checkbox[data-item-id="{self.item1.id}"]')
        checkbox1.uncheck()

        # Wait for WebSocket broadcast
        time.sleep(1)

        # Verify second browser received update
        checkbox2 = page2.locator(f'.item-checkbox[data-item-id="{self.item1.id}"]')
        expect(checkbox2).not_to_be_checked()

        # Verify visual feedback removed in second browser
        row2 = page2.locator(f'tr[data-item-id="{self.item1.id}"]')
        expect(row2).not_to_have_class('row-separated')

        page2.close()

    @pytest.mark.django_db
    def test_audit_log_records_unseparate_action(self, page: Page):
        """
        Test 8: Verify that unseparate actions are properly logged in audit trail
        """
        from apps.core.models import LogAuditoria

        # Mark item as separated
        from django.utils import timezone
        self.item1.separado = True
        self.item1.separado_por = self.test_user
        self.item1.separado_em = timezone.now()
        self.item1.save()

        # Clear existing audit logs for this test
        LogAuditoria.objects.filter(objeto_id=self.item1.id).delete()

        self.login(page)
        self.navigate_to_pedido_detalhe(page)

        # Uncheck the checkbox
        checkbox = page.locator(f'.item-checkbox[data-item-id="{self.item1.id}"]')
        checkbox.uncheck()

        # Wait for server response
        time.sleep(0.5)

        # Verify audit log was created
        audit_log = LogAuditoria.objects.filter(
            objeto_id=self.item1.id,
            acao='unseparar_item',
            usuario=self.test_user
        ).first()

        assert audit_log is not None, "Audit log should be created for unseparate action"
        assert audit_log.modelo == 'ItemPedido', "Audit log should reference ItemPedido model"
        assert 'separado_por_anterior' in audit_log.dados_novos, "Should log previous separator"

    @pytest.mark.django_db
    def test_pedido_status_updates_when_all_items_unseparated(self, page: Page):
        """
        Test 9: Verify pedido status changes to PENDENTE when all items are unseparated
        """
        # Mark all items as separated and set pedido status to EM_SEPARACAO
        from django.utils import timezone
        for item in [self.item1, self.item2, self.item3]:
            item.separado = True
            item.separado_por = self.test_user
            item.separado_em = timezone.now()
            item.save()

        self.pedido.status = 'EM_SEPARACAO'
        self.pedido.save()

        self.login(page)
        self.navigate_to_pedido_detalhe(page)

        # Uncheck all items
        for item in [self.item1, self.item2, self.item3]:
            checkbox = page.locator(f'.item-checkbox[data-item-id="{item.id}"]')
            checkbox.uncheck()
            time.sleep(0.3)

        # Verify pedido status changed to PENDENTE
        self.pedido.refresh_from_db()
        assert self.pedido.status == 'PENDENTE', "Pedido should return to PENDENTE when all items unseparated"

    @pytest.mark.django_db
    def test_error_handling_on_failed_unseparate(self, page: Page):
        """
        Test 10: Verify proper error handling when unseparate operation fails
        """
        # Mark item as separated
        from django.utils import timezone
        self.item1.separado = True
        self.item1.separado_por = self.test_user
        self.item1.separado_em = timezone.now()
        self.item1.save()

        self.login(page)
        self.navigate_to_pedido_detalhe(page)

        # Delete the item to cause a 404 error
        item_id = self.item1.id
        self.item1.delete()

        # Try to uncheck the checkbox
        checkbox = page.locator(f'.item-checkbox[data-item-id="{item_id}"]')

        # Setup alert listener
        alert_message = []

        def handle_dialog(dialog):
            alert_message.append(dialog.message)
            dialog.accept()

        page.on("dialog", handle_dialog)

        checkbox.uncheck()

        # Wait for error response
        time.sleep(0.5)

        # Verify error alert appeared
        assert len(alert_message) > 0, "Error alert should appear on failed unseparate"

        # Verify checkbox reverted to checked state
        expect(checkbox).to_be_checked()


# Pytest configuration for Playwright
@pytest.fixture(scope="function")
def page(browser: Browser):
    """Create a new page for each test"""
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture(scope="function")
def context(browser: Browser):
    """Create a new browser context for multi-browser tests"""
    context = browser.new_context()
    yield context
    context.close()


@pytest.fixture(scope="session")
def browser():
    """Create browser instance for the test session"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()
