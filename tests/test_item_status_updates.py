"""
Playwright E2E Tests for Item Status Updates
Tests the functionality of marking items as separado, em_compra, and substituido
"""
import pytest
from playwright.sync_api import Page, expect
import time
from django.test import LiveServerTestCase
from apps.core.models import Usuario, Pedido, ItemPedido, Produto


class TestItemStatusUpdates(LiveServerTestCase):
    """
    End-to-end tests for item status update functionality using Playwright
    """

    @classmethod
    def setUpClass(cls):
        """Set up test data once for all tests"""
        super().setUpClass()

        # Create test user (SEPARADOR with admin privileges)
        cls.test_user = Usuario.objects.create_user(
            numero_login=1234,
            nome='Test Separador',
            tipo='SEPARADOR',
            pin='1234'
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
            descricao='Test Product 3',
            preco=30.00,
            estoque_atual=25
        )

        # Create test order
        cls.test_order = Pedido.objects.create(
            numero_pedido='TEST-001',
            nome_cliente='Test Client',
            status='PENDENTE',
            criado_por=cls.test_user
        )

        # Create test items
        cls.item1 = ItemPedido.objects.create(
            pedido=cls.test_order,
            produto=cls.product1,
            quantidade_solicitada=10,
            preco_unitario=10.00
        )

        cls.item2 = ItemPedido.objects.create(
            pedido=cls.test_order,
            produto=cls.product2,
            quantidade_solicitada=5,
            preco_unitario=20.00
        )

        cls.item3 = ItemPedido.objects.create(
            pedido=cls.test_order,
            produto=cls.product3,
            quantidade_solicitada=2,
            preco_unitario=30.00
        )

    def login(self, page: Page):
        """Helper method to log in"""
        page.goto(f'{self.live_server_url}/login/')

        # Enter login credentials
        page.fill('input[name="numero_login"]', '1234')
        page.fill('input[name="pin"]', '1234')
        page.click('button[type="submit"]')

        # Wait for redirect to dashboard
        page.wait_for_url(f'{self.live_server_url}/dashboard/')

    def navigate_to_order(self, page: Page):
        """Helper method to navigate to order details"""
        page.goto(f'{self.live_server_url}/pedidos/{self.test_order.id}/')

        # Wait for the page to load
        page.wait_for_selector('h1:has-text("Detalhes do Pedido")', timeout=5000)

    @pytest.mark.django_db
    def test_javascript_file_loads(self, page: Page):
        """
        Test 1: Verify that pedido_detalhe.js loads correctly
        """
        self.login(page)
        self.navigate_to_order(page)

        # Check if the JavaScript file is loaded by verifying console has no errors
        # and that Alpine.js data is initialized
        alpine_initialized = page.evaluate("""
            () => {
                const element = document.querySelector('[x-data]');
                return element && element.__x !== undefined;
            }
        """)

        assert alpine_initialized, "Alpine.js should be initialized on the page"

        # Check if pedido_detalhe.js script tag exists
        script_tag = page.locator('script[src*="pedido_detalhe.js"]')
        expect(script_tag).to_have_count(1)

    @pytest.mark.django_db
    def test_checkbox_changes_item_status_to_separado(self, page: Page):
        """
        Test 2: Verify that clicking a checkbox marks item as separated
        and updates the UI
        """
        self.login(page)
        self.navigate_to_order(page)

        # Find the first item's checkbox
        checkbox = page.locator(f'input[type="checkbox"][data-item-id="{self.item1.id}"]').first()

        # Verify checkbox is initially unchecked
        expect(checkbox).not_to_be_checked()

        # Click the checkbox
        checkbox.check()

        # Wait for AJAX request to complete
        time.sleep(1)

        # Verify the item row has the 'row-separated' class
        row = page.locator(f'tr[data-item-id="{self.item1.id}"]')
        expect(row).to_have_class(lambda classes: 'row-separated' in classes)

        # Verify badge appears
        badge = row.locator('.badge:has-text("Separado")')
        expect(badge).to_be_visible()

        # Verify counter updated
        counter_separados = page.locator('.card:has-text("Separados")').locator('.text-2xl')
        expect(counter_separados).to_have_text('1')

        # Verify database was updated
        self.item1.refresh_from_db()
        assert self.item1.separado == True, "Item should be marked as separated in database"
        assert self.item1.separado_por == self.test_user, "Item should record who separated it"

    @pytest.mark.django_db
    def test_checkbox_uncheck_reverts_status(self, page: Page):
        """
        Test 3: Verify that unchecking a checkbox reverts the separation
        """
        # First, mark item as separated
        self.item1.separado = True
        self.item1.separado_por = self.test_user
        self.item1.save()

        self.login(page)
        self.navigate_to_order(page)

        # Find the checkbox (should be checked)
        checkbox = page.locator(f'input[type="checkbox"][data-item-id="{self.item1.id}"]').first()
        expect(checkbox).to_be_checked()

        # Uncheck it
        checkbox.uncheck()

        # Wait for AJAX request
        time.sleep(1)

        # Verify row no longer has separated class
        row = page.locator(f'tr[data-item-id="{self.item1.id}"]')
        expect(row).not_to_have_class(lambda classes: 'row-separated' in classes)

        # Verify counter updated
        counter_separados = page.locator('.card:has-text("Separados")').locator('.text-2xl')
        expect(counter_separados).to_have_text('0')

        # Verify database was updated
        self.item1.refresh_from_db()
        assert self.item1.separado == False, "Item should not be separated"

    @pytest.mark.django_db
    def test_marcar_compra_action(self, page: Page):
        """
        Test 4: Verify that marking an item for purchase works correctly
        """
        self.login(page)
        self.navigate_to_order(page)

        # Click the menu button for item
        menu_button = page.locator(f'button[data-item-id="{self.item2.id}"]').filter(has_text='⋮').first()
        menu_button.click()

        # Click "Marcar Compra" option
        compra_option = page.locator('a:has-text("Marcar Compra")')
        compra_option.click()

        # Wait for modal or confirmation
        time.sleep(1)

        # Confirm the action if there's a modal
        confirm_button = page.locator('button:has-text("Confirmar")')
        if confirm_button.is_visible():
            confirm_button.click()
            time.sleep(1)

        # Verify badge appears
        row = page.locator(f'tr[data-item-id="{self.item2.id}"]')
        badge = row.locator('.badge:has-text("Em Compra")')
        expect(badge).to_be_visible()

        # Verify counter
        counter_compra = page.locator('.card:has-text("Em Compra")').locator('.text-2xl')
        expect(counter_compra).to_have_text('1')

        # Verify database
        self.item2.refresh_from_db()
        assert self.item2.em_compra == True, "Item should be marked for purchase"

    @pytest.mark.django_db
    def test_substituir_item_action(self, page: Page):
        """
        Test 5: Verify that substituting an item works correctly
        """
        self.login(page)
        self.navigate_to_order(page)

        # Click the menu button
        menu_button = page.locator(f'button[data-item-id="{self.item3.id}"]').filter(has_text='⋮').first()
        menu_button.click()

        # Click "Substituir" option
        substituir_option = page.locator('a:has-text("Substituir")')
        substituir_option.click()

        # Wait for modal
        time.sleep(0.5)

        # Fill in substitute product
        substitute_input = page.locator('input[name="produto_substituto"]')
        substitute_input.fill('SUBSTITUTE-001 - Alternative Product')

        # Confirm
        confirm_button = page.locator('button:has-text("Confirmar")')
        confirm_button.click()

        # Wait for action to complete
        time.sleep(1)

        # Verify badge
        row = page.locator(f'tr[data-item-id="{self.item3.id}"]')
        badge = row.locator('.badge:has-text("Substituído")')
        expect(badge).to_be_visible()

        # Verify row has strikethrough
        expect(row).to_have_class(lambda classes: 'line-through' in classes)

        # Verify counter
        counter_substituido = page.locator('.card:has-text("Substituídos")').locator('.text-2xl')
        expect(counter_substituido).to_have_text('1')

        # Verify database
        self.item3.refresh_from_db()
        assert self.item3.substituido == True, "Item should be marked as substituted"
        assert 'SUBSTITUTE-001' in self.item3.produto_substituto, "Substitute product should be recorded"

    @pytest.mark.django_db
    def test_websocket_real_time_updates(self, page: Page):
        """
        Test 6: Verify WebSocket connection establishes and provides real-time updates
        """
        self.login(page)
        self.navigate_to_order(page)

        # Check WebSocket connection indicator (if present)
        ws_indicator = page.locator('.ws-indicator, .connection-status')
        if ws_indicator.is_visible():
            # Should show connected status
            expect(ws_indicator).to_have_class(lambda classes: 'connected' in classes or 'online' in classes)

        # Open a second browser context to simulate another user
        context2 = page.context.browser.new_context()
        page2 = context2.new_page()

        # Login with second user
        page2.goto(f'{self.live_server_url}/login/')
        page2.fill('input[name="numero_login"]', '1234')
        page2.fill('input[name="pin"]', '1234')
        page2.click('button[type="submit"]')
        page2.wait_for_url(f'{self.live_server_url}/dashboard/')

        # Navigate to same order
        page2.goto(f'{self.live_server_url}/pedidos/{self.test_order.id}/')
        page2.wait_for_selector('h1:has-text("Detalhes do Pedido")')

        # Mark item as separated in second browser
        checkbox2 = page2.locator(f'input[type="checkbox"][data-item-id="{self.item1.id}"]').first()
        checkbox2.check()
        time.sleep(1)

        # Verify first browser updates automatically via WebSocket
        row1 = page.locator(f'tr[data-item-id="{self.item1.id}"]')

        # Give some time for WebSocket message to propagate
        time.sleep(2)

        # First browser should show updated status
        expect(row1).to_have_class(lambda classes: 'row-separated' in classes)

        # Cleanup
        page2.close()
        context2.close()

    @pytest.mark.django_db
    def test_multiple_items_separation(self, page: Page):
        """
        Test 7: Verify separating multiple items updates counters correctly
        """
        self.login(page)
        self.navigate_to_order(page)

        # Check all three items
        for item in [self.item1, self.item2, self.item3]:
            checkbox = page.locator(f'input[type="checkbox"][data-item-id="{item.id}"]').first()
            checkbox.check()
            time.sleep(0.5)  # Small delay between clicks

        # Verify counter shows 3
        counter_separados = page.locator('.card:has-text("Separados")').locator('.text-2xl')
        expect(counter_separados).to_have_text('3')

        # Verify all items have separated class
        for item in [self.item1, self.item2, self.item3]:
            row = page.locator(f'tr[data-item-id="{item.id}"]')
            expect(row).to_have_class(lambda classes: 'row-separated' in classes)

        # Verify database
        for item in [self.item1, self.item2, self.item3]:
            item.refresh_from_db()
            assert item.separado == True, f"Item {item.id} should be separated"

    @pytest.mark.django_db
    def test_error_handling_on_failed_request(self, page: Page):
        """
        Test 8: Verify error handling when AJAX request fails
        """
        self.login(page)
        self.navigate_to_order(page)

        # Listen for console errors
        console_messages = []
        page.on("console", lambda msg: console_messages.append(msg))

        # Try to separate an invalid item (simulate error)
        # Inject a fake checkbox with invalid item ID
        page.evaluate("""
            () => {
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.setAttribute('data-item-id', '99999');
                checkbox.id = 'test-invalid-checkbox';
                document.body.appendChild(checkbox);
            }
        """)

        # Try to click it (should fail gracefully)
        invalid_checkbox = page.locator('#test-invalid-checkbox')
        invalid_checkbox.check()

        # Wait a bit for potential error
        time.sleep(1)

        # Checkbox should be reverted to unchecked state
        expect(invalid_checkbox).not_to_be_checked()

        # Should show error alert or message
        # (Implementation dependent - may vary)

    @pytest.mark.django_db
    def test_visual_feedback_row_colors(self, page: Page):
        """
        Test 9: Verify row colors change correctly for different statuses
        """
        self.login(page)
        self.navigate_to_order(page)

        # Mark item1 as separated
        checkbox1 = page.locator(f'input[type="checkbox"][data-item-id="{self.item1.id}"]').first()
        checkbox1.check()
        time.sleep(0.5)

        # Mark item2 for purchase
        menu_button2 = page.locator(f'button[data-item-id="{self.item2.id}"]').filter(has_text='⋮').first()
        menu_button2.click()
        page.locator('a:has-text("Marcar Compra")').click()
        time.sleep(0.5)

        # Mark item3 as substituted
        menu_button3 = page.locator(f'button[data-item-id="{self.item3.id}"]').filter(has_text='⋮').first()
        menu_button3.click()
        page.locator('a:has-text("Substituir")').click()
        page.locator('input[name="produto_substituto"]').fill('SUB-PRODUCT')
        page.locator('button:has-text("Confirmar")').click()
        time.sleep(0.5)

        # Verify different visual styles
        row1 = page.locator(f'tr[data-item-id="{self.item1.id}"]')
        row2 = page.locator(f'tr[data-item-id="{self.item2.id}"]')
        row3 = page.locator(f'tr[data-item-id="{self.item3.id}"]')

        # Check background colors via computed styles
        bg_color1 = row1.evaluate("el => window.getComputedStyle(el).backgroundColor")
        bg_color2 = row2.evaluate("el => window.getComputedStyle(el).backgroundColor")
        bg_color3 = row3.evaluate("el => window.getComputedStyle(el).backgroundColor")

        # They should be different (exact colors may vary)
        assert bg_color1 != bg_color2 or bg_color1 != bg_color3, "Different statuses should have different visual styles"

    @pytest.mark.django_db
    def test_csrf_token_present_in_requests(self, page: Page):
        """
        Test 10: Verify CSRF token is included in AJAX requests
        """
        self.login(page)
        self.navigate_to_order(page)

        # Intercept network requests
        requests_with_csrf = []

        def handle_request(request):
            if 'separar' in request.url:
                csrf_header = request.headers.get('x-csrftoken', '')
                if csrf_header:
                    requests_with_csrf.append(request.url)

        page.on("request", handle_request)

        # Trigger a separation action
        checkbox = page.locator(f'input[type="checkbox"][data-item-id="{self.item1.id}"]').first()
        checkbox.check()
        time.sleep(1)

        # Verify CSRF token was sent
        assert len(requests_with_csrf) > 0, "AJAX request should include CSRF token"


@pytest.fixture
def page(browser):
    """Fixture to provide a new page for each test"""
    context = browser.new_context()
    page = context.new_page()
    yield page
    page.close()
    context.close()


@pytest.fixture(scope="session")
def browser():
    """Fixture to provide a browser instance"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()
