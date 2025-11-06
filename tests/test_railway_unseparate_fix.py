"""
Test to verify the unseparate fix works in Railway production.
Tests the specific issue where unchecking items was causing HTTP 500.
"""
import os
import pytest
from playwright.sync_api import Page, expect


# Railway production URL
BASE_URL = "https://web-production-312d.up.railway.app"

# Credentials from environment (MUST be set to run tests)
# Format: numero_login (4 digits) and pin (4 digits)
NUMERO_LOGIN = os.getenv('RAILWAY_NUMERO_LOGIN', None)
PIN = os.getenv('RAILWAY_PIN', None)


@pytest.fixture(scope="module")
def page(browser):
    """Create a new page for the entire test module."""
    page = browser.new_page()
    yield page
    page.close()


@pytest.fixture(scope="module")
def authenticated_page(page):
    """Login once and reuse the session."""
    # Check if credentials are provided
    if not NUMERO_LOGIN or not PIN:
        pytest.skip(
            "Railway credentials not provided. "
            "Set RAILWAY_NUMERO_LOGIN and RAILWAY_PIN environment variables."
        )

    print(f"\n[LOGIN] Authenticating to {BASE_URL}...")

    # Navigate to login page (root redirects to login if not authenticated)
    page.goto(f"{BASE_URL}/")
    page.wait_for_load_state('networkidle')

    # Fill login form - PMCELL uses numero_login and pin (4 digits each)
    page.fill('input[name="numero_login"]', NUMERO_LOGIN)
    page.fill('input[name="pin"]', PIN)

    # Submit form
    page.click('button[type="submit"]')

    # Wait for redirect to dashboard
    page.wait_for_url(f"{BASE_URL}/")

    print("[LOGIN] ✓ Authentication successful")

    yield page


def test_unseparate_no_http_500(authenticated_page: Page):
    """
    Test that unchecking a separated item does NOT cause HTTP 500.
    This is the main fix we're verifying.
    """
    page = authenticated_page

    print("\n[TEST] Starting unseparate HTTP 500 fix test...")

    # Navigate to pedidos list
    page.goto(f"{BASE_URL}/pedidos/")
    page.wait_for_load_state('networkidle')

    # Find first pedido with items
    pedido_link = page.locator('a[href*="/pedidos/"]').first
    if pedido_link.count() == 0:
        pytest.skip("No pedidos available for testing")

    pedido_url = pedido_link.get_attribute('href')
    print(f"[TEST] Opening pedido: {pedido_url}")

    # Navigate to pedido detail
    page.goto(f"{BASE_URL}{pedido_url}")
    page.wait_for_load_state('networkidle')

    # Find first unseparated item
    checkbox = page.locator('input.item-checkbox:not(:checked)').first
    if checkbox.count() == 0:
        print("[TEST] No unseparated items found, trying to unseparate an already separated item...")
        checkbox = page.locator('input.item-checkbox:checked').first

        if checkbox.count() == 0:
            pytest.skip("No items available for testing")

    # Get item ID
    row = checkbox.locator('xpath=ancestor::tr[@data-item-id]')
    item_id = row.get_attribute('data-item-id')
    print(f"[TEST] Testing with item ID: {item_id}")

    # Setup response listener to catch HTTP 500 errors
    http_500_occurred = []

    def handle_response(response):
        if response.status == 500:
            http_500_occurred.append(response)
            print(f"[ERROR] HTTP 500 detected: {response.url}")

    page.on("response", handle_response)

    # Check the checkbox (separate item)
    if not checkbox.is_checked():
        print(f"[TEST] Checking checkbox for item {item_id}...")
        checkbox.check()
        page.wait_for_timeout(1000)  # Wait for separation
        print("[TEST] ✓ Item separated")

    # Now uncheck the checkbox (unseparate item) - THIS IS THE FIX WE'RE TESTING
    print(f"[TEST] Unchecking checkbox for item {item_id}...")
    checkbox.uncheck()

    # Wait for the unseparate request to complete
    page.wait_for_timeout(2000)

    # Remove response listener
    page.remove_listener("response", handle_response)

    # ASSERTION: No HTTP 500 should have occurred
    if http_500_occurred:
        pytest.fail(f"HTTP 500 error occurred when unseparating item {item_id}. FIX FAILED!")

    print("[TEST] ✓ No HTTP 500 error - Fix successful!")

    # Verify checkbox is unchecked
    expect(checkbox).not_to_be_checked()
    print("[TEST] ✓ Checkbox is unchecked")

    # Verify item is no longer visually separated (row-separated class removed)
    expect(row).not_to_have_class('row-separated')
    print("[TEST] ✓ Row visual styling updated")

    print("[TEST] ✅ All checks passed - Unseparate fix verified!")


def test_separate_and_unseparate_cycle(authenticated_page: Page):
    """
    Test complete cycle: separate → unseparate → separate again
    Ensures the fix works across multiple operations.
    """
    page = authenticated_page

    print("\n[TEST] Starting separate/unseparate cycle test...")

    # Navigate to pedidos list
    page.goto(f"{BASE_URL}/pedidos/")
    page.wait_for_load_state('networkidle')

    # Find first pedido
    pedido_link = page.locator('a[href*="/pedidos/"]').first
    if pedido_link.count() == 0:
        pytest.skip("No pedidos available for testing")

    pedido_url = pedido_link.get_attribute('href')
    page.goto(f"{BASE_URL}{pedido_url}")
    page.wait_for_load_state('networkidle')

    # Find first item
    checkbox = page.locator('input.item-checkbox').first
    if checkbox.count() == 0:
        pytest.skip("No items available for testing")

    row = checkbox.locator('xpath=ancestor::tr[@data-item-id]')
    item_id = row.get_attribute('data-item-id')

    print(f"[TEST] Testing cycle with item {item_id}...")

    # Track HTTP 500 errors
    http_500_occurred = []

    def handle_response(response):
        if response.status == 500:
            http_500_occurred.append(response)

    page.on("response", handle_response)

    # Cycle 1: Separate
    print("[TEST] Cycle 1: Separating...")
    if not checkbox.is_checked():
        checkbox.check()
        page.wait_for_timeout(1000)
    expect(checkbox).to_be_checked()
    print("[TEST] ✓ Separated")

    # Cycle 2: Unseparate
    print("[TEST] Cycle 2: Unseparating...")
    checkbox.uncheck()
    page.wait_for_timeout(1000)
    expect(checkbox).not_to_be_checked()
    print("[TEST] ✓ Unseparated")

    # Cycle 3: Separate again
    print("[TEST] Cycle 3: Separating again...")
    checkbox.check()
    page.wait_for_timeout(1000)
    expect(checkbox).to_be_checked()
    print("[TEST] ✓ Separated again")

    # Cycle 4: Unseparate again
    print("[TEST] Cycle 4: Unseparating again...")
    checkbox.uncheck()
    page.wait_for_timeout(1000)
    expect(checkbox).not_to_be_checked()
    print("[TEST] ✓ Unseparated again")

    page.remove_listener("response", handle_response)

    # Verify no HTTP 500 errors occurred during entire cycle
    if http_500_occurred:
        pytest.fail(f"HTTP 500 error occurred during cycle. URLs: {[r.url for r in http_500_occurred]}")

    print("[TEST] ✅ Complete cycle successful - No HTTP 500 errors!")


def test_console_errors(authenticated_page: Page):
    """
    Monitor browser console for errors during unseparate operations.
    """
    page = authenticated_page

    print("\n[TEST] Starting console error monitoring test...")

    console_errors = []

    def handle_console(msg):
        if msg.type == 'error':
            console_errors.append(msg.text)
            print(f"[CONSOLE ERROR] {msg.text}")

    page.on("console", handle_console)

    # Navigate to pedidos
    page.goto(f"{BASE_URL}/pedidos/")
    page.wait_for_load_state('networkidle')

    pedido_link = page.locator('a[href*="/pedidos/"]').first
    if pedido_link.count() == 0:
        pytest.skip("No pedidos available for testing")

    pedido_url = pedido_link.get_attribute('href')
    page.goto(f"{BASE_URL}{pedido_url}")
    page.wait_for_load_state('networkidle')

    # Find and click checkbox
    checkbox = page.locator('input.item-checkbox').first
    if checkbox.count() == 0:
        pytest.skip("No items available for testing")

    # Check and uncheck
    if not checkbox.is_checked():
        checkbox.check()
        page.wait_for_timeout(1000)

    checkbox.uncheck()
    page.wait_for_timeout(2000)

    page.remove_listener("console", handle_console)

    # Filter out known warnings (like Tailwind CDN warning)
    serious_errors = [e for e in console_errors if 'tailwindcss' not in e.lower() and 'cdn' not in e.lower()]

    if serious_errors:
        pytest.fail(f"Console errors detected: {serious_errors}")

    print("[TEST] ✅ No serious console errors detected!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--headed"])
