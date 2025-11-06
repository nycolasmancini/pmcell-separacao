#!/usr/bin/env python3
"""
Test script for separation screen fixes using Playwright
Tests all 3 scenarios that were reported as broken:
1. Uncheck product (should not return 500 error)
2. Product substitution (should update UI in real-time)
3. Mark to buy (should update UI in real-time)
"""

import asyncio
import sys
from playwright.async_api import async_playwright, expect

# Railway production URL
BASE_URL = "https://web-production-312d.up.railway.app"

# Test credentials (update if needed)
TEST_USERNAME = "admin"
TEST_PASSWORD = "admin123"


async def login(page):
    """Login to the application"""
    print("🔐 Logging in...")
    await page.goto(f"{BASE_URL}/login/")
    await page.fill('input[name="username"]', TEST_USERNAME)
    await page.fill('input[name="password"]', TEST_PASSWORD)
    await page.click('button[type="submit"]')
    await page.wait_for_url(f"{BASE_URL}/dashboard/", timeout=10000)
    print("✅ Login successful")


async def test_uncheck_product(page):
    """Test #1: Uncheck product should work without 500 error"""
    print("\n" + "="*60)
    print("TEST #1: Uncheck Product (HTTP 500 Error Fix)")
    print("="*60)

    # Navigate to a pedido detalhe page (assuming pedido ID 2 exists)
    await page.goto(f"{BASE_URL}/pedido/2/")
    print("📄 Navigated to pedido detalhe page")

    # Wait for page to load
    await page.wait_for_selector('table tbody tr', timeout=10000)
    print("✅ Page loaded")

    # Find first unchecked item and check it
    unchecked_checkbox = await page.query_selector('input[type="checkbox"]:not(:checked)')
    if not unchecked_checkbox:
        print("⚠️  No unchecked items found, looking for checked item to uncheck...")
        checked_checkbox = await page.query_selector('input[type="checkbox"]:checked')
        if not checked_checkbox:
            print("❌ No checkboxes found at all!")
            return False

        # Get item ID
        row = await checked_checkbox.evaluate_handle('el => el.closest("tr")')
        item_id = await row.evaluate('el => el.getAttribute("data-item-id")')

        print(f"🔲 Found checked item {item_id}, will test unchecking it...")

        # Uncheck the item
        await checked_checkbox.click()
        print("🖱️  Clicked to uncheck item")

        # Wait a moment for the request to complete
        await page.wait_for_timeout(2000)

        # Check console for errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg) if msg.type == "error" else None)

        # Verify no 500 error in console
        await page.wait_for_timeout(1000)

        has_500_error = any("500" in str(msg) for msg in console_errors)

        if has_500_error:
            print("❌ HTTP 500 error detected in console!")
            return False
        else:
            print("✅ No HTTP 500 error - fix successful!")
            return True

    else:
        # Check the item first, then uncheck it
        await unchecked_checkbox.click()
        print("🖱️  Checked item first")
        await page.wait_for_timeout(2000)

        # Now uncheck it
        await unchecked_checkbox.click()
        print("🖱️  Unchecked item")

        # Wait for response
        await page.wait_for_timeout(2000)

        # Check for errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg) if msg.type == "error" else None)
        await page.wait_for_timeout(1000)

        has_500_error = any("500" in str(msg) for msg in console_errors)

        if has_500_error:
            print("❌ HTTP 500 error detected!")
            return False
        else:
            print("✅ Uncheck successful without 500 error!")
            return True


async def test_product_substitution(page):
    """Test #2: Product substitution should update UI in real-time"""
    print("\n" + "="*60)
    print("TEST #2: Product Substitution Real-time Update")
    print("="*60)

    await page.goto(f"{BASE_URL}/pedido/2/")
    print("📄 Navigated to pedido detalhe page")

    await page.wait_for_selector('table tbody tr', timeout=10000)
    print("✅ Page loaded")

    # Find a product that can be substituted (first row)
    first_row = await page.query_selector('table tbody tr')
    if not first_row:
        print("❌ No items found!")
        return False

    # Click substitute button (look for "Substituir" button)
    substitute_button = await first_row.query_selector('button:has-text("Substituir")')
    if not substitute_button:
        print("⚠️  No substitute button found on first item, skipping test")
        return None  # Skip test if button not available

    print("🔄 Found substitute button, clicking...")
    await substitute_button.click()

    # Wait for modal or input field
    await page.wait_for_timeout(1000)

    # Fill in substitute product name
    substitute_input = await page.query_selector('input[placeholder*="substituto"]')
    if substitute_input:
        await substitute_input.fill("PRODUTO TESTE SUBSTITUIDO")
        print("📝 Entered substitute product name")

        # Confirm substitution
        confirm_button = await page.query_selector('button:has-text("Confirmar")')
        if confirm_button:
            await confirm_button.click()
            print("✅ Confirmed substitution")

            # Wait for real-time update (should update without page refresh)
            await page.wait_for_timeout(2000)

            # Check if UI updated (look for blue badge or substitution indicator)
            row_after = await page.query_selector('table tbody tr')
            has_substitution_indicator = await row_after.query_selector('.bg-blue-100, [class*="blue"]')

            if has_substitution_indicator:
                print("✅ UI updated in real-time with substitution indicator!")
                return True
            else:
                print("⚠️  Substitution may have succeeded but UI didn't update immediately")
                return False

    print("⚠️  Could not complete substitution test")
    return None


async def test_mark_to_buy(page):
    """Test #3: Mark to buy should update UI in real-time"""
    print("\n" + "="*60)
    print("TEST #3: Mark to Buy Real-time Update")
    print("="*60)

    await page.goto(f"{BASE_URL}/pedido/2/")
    print("📄 Navigated to pedido detalhe page")

    await page.wait_for_selector('table tbody tr', timeout=10000)
    print("✅ Page loaded")

    # Find first row
    first_row = await page.query_selector('table tbody tr')
    if not first_row:
        print("❌ No items found!")
        return False

    # Look for "Comprar" button
    comprar_button = await first_row.query_selector('button:has-text("Comprar")')
    if not comprar_button:
        print("⚠️  No 'Comprar' button found on first item, skipping test")
        return None

    print("🛒 Found 'Comprar' button, clicking...")
    await comprar_button.click()

    # Wait for real-time update
    await page.wait_for_timeout(2000)

    # Check if status badge updated to yellow "Em Compra"
    row_after = await page.query_selector('table tbody tr')
    yellow_badge = await row_after.query_selector('.bg-yellow-100, [class*="yellow"]')

    if yellow_badge:
        badge_text = await yellow_badge.text_content()
        if "Compra" in badge_text:
            print("✅ UI updated in real-time with 'Em Compra' status!")
            return True
        else:
            print(f"⚠️  Badge found but text is: {badge_text}")
            return False
    else:
        print("⚠️  Mark to buy may have succeeded but UI didn't update immediately")
        return False


async def test_websocket_connection(page):
    """Test that WebSocket connection is established successfully"""
    print("\n" + "="*60)
    print("BONUS TEST: WebSocket Connection")
    print("="*60)

    await page.goto(f"{BASE_URL}/pedido/2/")
    print("📄 Navigated to pedido detalhe page")

    # Capture console logs
    websocket_logs = []

    def handle_console(msg):
        text = msg.text
        if "WebSocket" in text:
            websocket_logs.append(text)
            print(f"📡 {text}")

    page.on("console", handle_console)

    # Wait for WebSocket connection attempt
    await page.wait_for_timeout(3000)

    # Check if connection succeeded (no error 1006)
    has_connection_error = any("1006" in log or "bad response" in log for log in websocket_logs)
    has_connection_success = any("conectado" in log.lower() for log in websocket_logs)

    if has_connection_error:
        print("❌ WebSocket connection failed (error 1006)")
        return False
    elif has_connection_success:
        print("✅ WebSocket connected successfully!")
        return True
    else:
        print("⚠️  Could not determine WebSocket status from logs")
        return None


async def main():
    """Main test runner"""
    print("🚀 Starting Separation Screen Fix Tests")
    print(f"📍 Testing URL: {BASE_URL}")
    print()

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)  # Set to True for CI/CD
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Login first
            await login(page)

            # Run tests
            results = {}

            # Test WebSocket connection first
            results['websocket'] = await test_websocket_connection(page)

            # Test #1: Uncheck product
            results['uncheck'] = await test_uncheck_product(page)

            # Test #2: Product substitution
            results['substitution'] = await test_product_substitution(page)

            # Test #3: Mark to buy
            results['mark_to_buy'] = await test_mark_to_buy(page)

            # Print summary
            print("\n" + "="*60)
            print("TEST SUMMARY")
            print("="*60)

            passed = sum(1 for v in results.values() if v is True)
            failed = sum(1 for v in results.values() if v is False)
            skipped = sum(1 for v in results.values() if v is None)

            print(f"✅ Passed: {passed}")
            print(f"❌ Failed: {failed}")
            print(f"⚠️  Skipped: {skipped}")
            print()

            for test_name, result in results.items():
                status = "✅ PASS" if result is True else ("❌ FAIL" if result is False else "⚠️  SKIP")
                print(f"{status} - {test_name}")

            print("="*60)

            # Return exit code
            return 0 if failed == 0 else 1

        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return 1

        finally:
            await browser.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
