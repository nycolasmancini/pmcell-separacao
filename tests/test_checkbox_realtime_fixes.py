"""
Playwright test suite for checkbox and real-time update fixes

Tests:
1. Unsubstituting items via checkbox works
2. Real-time updates show immediately without page refresh
3. Substitution info is removed when unmarking
4. Purchase info is removed when unmarking
"""
import asyncio
from playwright.async_api import async_playwright, expect
import os
from datetime import datetime


class TestCheckboxRealtimeFixes:
    """Test suite for checkbox and real-time update functionality"""

    def __init__(self):
        self.base_url = "https://web-production-312d.up.railway.app"
        self.username = "nycolasadm"
        self.pin = "123"
        self.screenshot_dir = "test_screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    async def take_screenshot(self, page, name):
        """Take screenshot with timestamp"""
        filename = f"{self.screenshot_dir}/{self.timestamp}_{name}.png"
        await page.screenshot(path=filename, full_page=True)
        print(f"[Screenshot] {filename}")
        return filename

    async def login(self, page):
        """Perform login"""
        print("\n[LOGIN] Starting login process...")
        await page.goto(self.base_url)
        await self.take_screenshot(page, "01_homepage")

        # Click login button
        await page.click('text=Entrar')
        await page.wait_for_load_state('networkidle')
        await self.take_screenshot(page, "02_login_page")

        # Fill credentials
        await page.fill('input[name="username"]', self.username)
        await page.fill('input[name="pin"]', self.pin)
        await self.take_screenshot(page, "03_credentials_filled")

        # Submit login
        await page.click('button[type="submit"]')
        await page.wait_for_load_state('networkidle')
        await self.take_screenshot(page, "04_after_login")

        # Verify we're logged in
        await expect(page.locator('text=Dashboard')).to_be_visible(timeout=10000)
        print("[LOGIN] Login successful!")

    async def test_unsubstitute_item(self, page):
        """
        Test 1: Verify substituted items can be unmarked via checkbox

        Steps:
        1. Navigate to order details page
        2. Mark an item as substituted
        3. Click checkbox to unmark it
        4. Verify substitution info is removed
        5. Verify item returns to Pendente status
        """
        print("\n[TEST 1] Testing unsubstitute functionality...")

        # Navigate to order details (assuming order ID 2 exists)
        order_url = f"{self.base_url}/pedido/2/"
        await page.goto(order_url)
        await page.wait_for_load_state('networkidle')
        await self.take_screenshot(page, "05_order_details")

        # Find first pending item
        first_item_row = page.locator('tr[data-item-id]').first
        item_id = await first_item_row.get_attribute('data-item-id')
        print(f"[TEST 1] Selected item ID: {item_id}")

        # Open dropdown menu for the item
        await first_item_row.locator('button.dropdown-toggle').click()
        await page.wait_for_timeout(500)
        await self.take_screenshot(page, "06_dropdown_opened")

        # Click "Substituído" option
        await page.click('text=Substituído')
        await page.wait_for_timeout(500)

        # Fill substitution modal
        await expect(page.locator('#substitutoModal')).to_be_visible()
        await page.fill('input[name="produto_substituto"]', 'Produto Teste XYZ')
        await self.take_screenshot(page, "07_substitution_modal")

        # Confirm substitution
        await page.click('button:has-text("Confirmar")')
        await page.wait_for_timeout(2000)  # Wait for WebSocket update
        await self.take_screenshot(page, "08_after_substitution")

        # Verify item is marked as substituted
        status_badge = first_item_row.locator('.status-badge')
        await expect(status_badge).to_contain_text('Substituído')

        # Verify substitution info is visible
        substitution_info = first_item_row.locator('.text-blue-600')
        await expect(substitution_info).to_be_visible()
        print("[TEST 1] Item marked as substituted successfully")

        # NOW THE CRITICAL TEST: Uncheck the checkbox
        print("[TEST 1] Attempting to uncheck substituted item...")
        checkbox = first_item_row.locator('.item-checkbox')
        await expect(checkbox).to_be_checked()

        await checkbox.click()
        await page.wait_for_timeout(2000)  # Wait for server response and WebSocket
        await self.take_screenshot(page, "09_after_uncheck")

        # Verify checkbox is unchecked
        await expect(checkbox).not_to_be_checked()
        print("[TEST 1] Checkbox unchecked successfully")

        # Verify substitution info is removed
        substitution_divs = await first_item_row.locator('.text-blue-600').count()
        assert substitution_divs == 0, "Substitution info should be removed"
        print("[TEST 1] Substitution info removed")

        # Verify status is back to Pendente
        await expect(status_badge).to_contain_text('Pendente')
        print("[TEST 1] Status returned to Pendente")

        print("[TEST 1] ✅ TEST PASSED: Unsubstitute functionality works!")
        return True

    async def test_realtime_updates(self, page, context):
        """
        Test 2: Verify real-time updates work without page refresh

        Steps:
        1. Open same order in two browser tabs
        2. Mark item in tab 1
        3. Verify update appears in tab 2 without refresh
        """
        print("\n[TEST 2] Testing real-time updates...")

        # Create second page (tab 2)
        page2 = await context.new_page()

        # Navigate both tabs to order details
        order_url = f"{self.base_url}/pedido/2/"
        await page.goto(order_url)
        await page2.goto(order_url)
        await page.wait_for_load_state('networkidle')
        await page2.wait_for_load_state('networkidle')

        await self.take_screenshot(page, "10_tab1_before")
        await self.take_screenshot(page2, "11_tab2_before")

        # In tab 1, mark first item for purchase
        first_item_row = page.locator('tr[data-item-id]').first
        item_id = await first_item_row.get_attribute('data-item-id')

        # Open dropdown
        await first_item_row.locator('button.dropdown-toggle').click()
        await page.wait_for_timeout(500)

        # Click "Para Comprar"
        await page.click('text=Para Comprar')
        await page.wait_for_timeout(3000)  # Wait for WebSocket propagation
        await self.take_screenshot(page, "12_tab1_after_mark")

        # In tab 2, verify real-time update appeared
        tab2_item_row = page2.locator(f'tr[data-item-id="{item_id}"]')
        tab2_status = tab2_item_row.locator('.status-badge')

        await self.take_screenshot(page2, "13_tab2_after_realtime")

        # Verify status updated in real-time
        await expect(tab2_status).to_contain_text('Em Compra', timeout=5000)
        print("[TEST 2] Real-time update received in tab 2!")

        # Now unmark in tab 1 and verify tab 2 updates
        checkbox = first_item_row.locator('.item-checkbox')
        await checkbox.click()
        await page.wait_for_timeout(3000)
        await self.take_screenshot(page, "14_tab1_after_unmark")

        # Verify tab 2 received unmark update
        await expect(tab2_status).to_contain_text('Pendente', timeout=5000)
        await self.take_screenshot(page2, "15_tab2_after_unmark_realtime")

        print("[TEST 2] ✅ TEST PASSED: Real-time updates work correctly!")

        await page2.close()
        return True

    async def test_purchase_removal(self, page):
        """
        Test 3: Verify purchase info is removed when unmarking
        """
        print("\n[TEST 3] Testing purchase info removal...")

        order_url = f"{self.base_url}/pedido/2/"
        await page.goto(order_url)
        await page.wait_for_load_state('networkidle')

        # Mark item for purchase
        first_item_row = page.locator('tr[data-item-id]').first

        await first_item_row.locator('button.dropdown-toggle').click()
        await page.wait_for_timeout(500)
        await page.click('text=Para Comprar')
        await page.wait_for_timeout(2000)
        await self.take_screenshot(page, "16_marked_for_purchase")

        # Verify purchase badge exists
        status_badge = first_item_row.locator('.status-badge')
        await expect(status_badge).to_contain_text('Em Compra')

        # Uncheck
        checkbox = first_item_row.locator('.item-checkbox')
        await checkbox.click()
        await page.wait_for_timeout(2000)
        await self.take_screenshot(page, "17_after_unmark_purchase")

        # Verify purchase badge removed
        await expect(status_badge).to_contain_text('Pendente')

        # Verify no purchase badges remain in action buttons area
        purchase_badges = await first_item_row.locator('.bg-yellow-100.text-yellow-800').count()
        assert purchase_badges == 0, "Purchase badges should be removed"

        print("[TEST 3] ✅ TEST PASSED: Purchase info removed correctly!")
        return True

    async def run_all_tests(self):
        """Run all test cases"""
        print("=" * 70)
        print("CHECKBOX AND REAL-TIME UPDATE FIX - TEST SUITE")
        print("=" * 70)
        print(f"Base URL: {self.base_url}")
        print(f"Timestamp: {self.timestamp}")
        print("=" * 70)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()

            try:
                # Login
                await self.login(page)

                # Run tests
                test_results = {
                    'test_unsubstitute_item': False,
                    'test_realtime_updates': False,
                    'test_purchase_removal': False
                }

                try:
                    test_results['test_unsubstitute_item'] = await self.test_unsubstitute_item(page)
                except Exception as e:
                    print(f"[TEST 1] ❌ FAILED: {str(e)}")
                    await self.take_screenshot(page, "ERROR_test1")

                try:
                    test_results['test_realtime_updates'] = await self.test_realtime_updates(page, context)
                except Exception as e:
                    print(f"[TEST 2] ❌ FAILED: {str(e)}")
                    await self.take_screenshot(page, "ERROR_test2")

                try:
                    test_results['test_purchase_removal'] = await self.test_purchase_removal(page)
                except Exception as e:
                    print(f"[TEST 3] ❌ FAILED: {str(e)}")
                    await self.take_screenshot(page, "ERROR_test3")

                # Print results
                print("\n" + "=" * 70)
                print("TEST RESULTS SUMMARY")
                print("=" * 70)
                for test_name, passed in test_results.items():
                    status = "✅ PASSED" if passed else "❌ FAILED"
                    print(f"{test_name}: {status}")

                all_passed = all(test_results.values())
                print("=" * 70)
                if all_passed:
                    print("🎉 ALL TESTS PASSED!")
                else:
                    print("⚠️  SOME TESTS FAILED")
                print("=" * 70)

                return all_passed

            except Exception as e:
                print(f"\n❌ CRITICAL ERROR: {str(e)}")
                await self.take_screenshot(page, "CRITICAL_ERROR")
                import traceback
                traceback.print_exc()
                return False
            finally:
                await browser.close()


async def main():
    """Main entry point"""
    tester = TestCheckboxRealtimeFixes()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
