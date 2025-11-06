"""
Manual verification script to test that the fix is working
This script performs basic checks without requiring full E2E infrastructure
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pmcell_settings.settings')
django.setup()

from django.test import Client
from apps.core.models import Usuario, Pedido, ItemPedido, Produto
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_template_block_exists():
    """Test 1: Verify extra_head block exists in base.html"""
    print_section("TEST 1: Template Block Verification")

    base_template_path = 'templates/base.html'
    with open(base_template_path, 'r') as f:
        content = f.read()

    if '{% block extra_head %}{% endblock %}' in content:
        print("✓ SUCCESS: extra_head block found in base.html")
        return True
    else:
        print("✗ FAIL: extra_head block NOT found in base.html")
        return False


def test_javascript_file_exists():
    """Test 2: Verify pedido_detalhe.js exists"""
    print_section("TEST 2: JavaScript File Verification")

    js_paths = [
        'static/js/pedido_detalhe.js',
        'staticfiles/js/pedido_detalhe.js'
    ]

    all_exist = True
    for path in js_paths:
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"✓ SUCCESS: {path} exists ({size} bytes)")
        else:
            print(f"✗ FAIL: {path} NOT found")
            all_exist = False

    return all_exist


def test_pedido_detalhe_template_includes_js():
    """Test 3: Verify pedido_detalhe.html includes the JavaScript file"""
    print_section("TEST 3: Template JavaScript Inclusion")

    template_path = 'templates/pedido_detalhe.html'
    with open(template_path, 'r') as f:
        content = f.read()

    checks = [
        ('{% block extra_head %}', 'extra_head block usage'),
        ('pedido_detalhe.js', 'JavaScript file reference'),
        ('<script', 'script tag'),
    ]

    all_passed = True
    for check_str, description in checks:
        if check_str in content:
            print(f"✓ SUCCESS: {description} found")
        else:
            print(f"✗ FAIL: {description} NOT found")
            all_passed = False

    return all_passed


def test_csrf_token_in_template():
    """Test 4: Verify CSRF token is available in template"""
    print_section("TEST 4: CSRF Token Configuration")

    template_path = 'templates/pedido_detalhe.html'
    with open(template_path, 'r') as f:
        content = f.read()

    if '{% csrf_token %}' in content or 'csrftoken' in content:
        print("✓ SUCCESS: CSRF token handling found in template")
        return True
    else:
        print("✗ FAIL: CSRF token NOT found in template")
        return False


def test_database_models():
    """Test 5: Verify database models are correctly configured"""
    print_section("TEST 5: Database Model Verification")

    try:
        # Check if we can query models
        user_count = Usuario.objects.count()
        pedido_count = Pedido.objects.count()
        item_count = ItemPedido.objects.count()
        produto_count = Produto.objects.count()

        print(f"✓ SUCCESS: Database models accessible")
        print(f"  - Usuários: {user_count}")
        print(f"  - Pedidos: {pedido_count}")
        print(f"  - Itens: {item_count}")
        print(f"  - Produtos: {produto_count}")
        return True
    except Exception as e:
        print(f"✗ FAIL: Database error: {e}")
        return False


def test_api_endpoints_exist():
    """Test 6: Verify API endpoints are registered"""
    print_section("TEST 6: API Endpoints Verification")

    from django.urls import reverse

    endpoints = [
        ('separar_item', 'Separar Item'),
        ('marcar_compra', 'Marcar Compra'),
        ('substituir_item', 'Substituir Item'),
    ]

    all_exist = True
    for url_name, description in endpoints:
        try:
            # Try to reverse with a dummy ID
            url = reverse(url_name, kwargs={'item_id': 1})
            print(f"✓ SUCCESS: {description} endpoint registered at {url}")
        except Exception as e:
            print(f"✗ FAIL: {description} endpoint error: {e}")
            all_exist = False

    return all_exist


def test_item_status_fields():
    """Test 7: Verify ItemPedido model has status fields"""
    print_section("TEST 7: ItemPedido Model Fields")

    from apps.core.models import ItemPedido

    required_fields = [
        'separado',
        'em_compra',
        'substituido',
        'separado_por',
        'separado_em',
        'marcado_compra_por',
        'marcado_compra_em',
        'produto_substituto'
    ]

    all_exist = True
    for field_name in required_fields:
        if hasattr(ItemPedido, field_name):
            print(f"✓ SUCCESS: ItemPedido.{field_name} field exists")
        else:
            print(f"✗ FAIL: ItemPedido.{field_name} field NOT found")
            all_exist = False

    return all_exist


def test_create_test_data():
    """Test 8: Create test data and verify it works"""
    print_section("TEST 8: Test Data Creation")

    try:
        # Check if test user exists, create if not
        user, created = Usuario.objects.get_or_create(
            numero_login=9999,
            defaults={
                'nome': 'Test User',
                'tipo': 'SEPARADOR',
            }
        )
        if created:
            user.set_pin('9999')
            user.save()
            print(f"✓ Created test user: {user.numero_login} - {user.nome}")
        else:
            print(f"✓ Test user already exists: {user.numero_login} - {user.nome}")

        # Check if test product exists
        produto, created = Produto.objects.get_or_create(
            codigo='TEST-FIX',
            defaults={
                'descricao': 'Test Product for Fix Verification',
                'preco': 99.99,
                'estoque_atual': 100
            }
        )
        if created:
            print(f"✓ Created test product: {produto.codigo}")
        else:
            print(f"✓ Test product already exists: {produto.codigo}")

        # Check if test order exists
        pedido, created = Pedido.objects.get_or_create(
            numero_pedido='FIX-TEST-001',
            defaults={
                'nome_cliente': 'Test Client for Fix',
                'status': 'PENDENTE',
                'criado_por': user
            }
        )
        if created:
            print(f"✓ Created test order: {pedido.numero_pedido}")
        else:
            print(f"✓ Test order already exists: {pedido.numero_pedido}")

        # Create test item
        item, created = ItemPedido.objects.get_or_create(
            pedido=pedido,
            produto=produto,
            defaults={
                'quantidade_solicitada': 10,
                'preco_unitario': 99.99
            }
        )
        if created:
            print(f"✓ Created test item: {item.id}")
        else:
            print(f"✓ Test item already exists: {item.id}")

        print(f"\n✓ SUCCESS: Test data ready")
        print(f"  Access test order at: /pedidos/{pedido.id}/")
        print(f"  Login with: 9999 / PIN: 9999")

        return True
    except Exception as e:
        print(f"✗ FAIL: Error creating test data: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_static_files_configuration():
    """Test 9: Verify static files are configured correctly"""
    print_section("TEST 9: Static Files Configuration")

    from django.conf import settings

    checks = [
        (hasattr(settings, 'STATIC_URL'), 'STATIC_URL defined'),
        (hasattr(settings, 'STATIC_ROOT'), 'STATIC_ROOT defined'),
        (hasattr(settings, 'STATICFILES_DIRS'), 'STATICFILES_DIRS defined'),
        (os.path.exists('staticfiles'), 'staticfiles directory exists'),
    ]

    all_passed = True
    for condition, description in checks:
        if condition:
            print(f"✓ SUCCESS: {description}")
        else:
            print(f"✗ FAIL: {description}")
            all_passed = False

    if hasattr(settings, 'STATIC_URL'):
        print(f"  STATIC_URL: {settings.STATIC_URL}")
    if hasattr(settings, 'STATIC_ROOT'):
        print(f"  STATIC_ROOT: {settings.STATIC_ROOT}")

    return all_passed


def main():
    """Run all verification tests"""
    print("\n" + "="*60)
    print("  PMCELL FIX VERIFICATION TEST SUITE")
    print("  Testing Item Status Update Functionality")
    print("="*60)

    tests = [
        test_template_block_exists,
        test_javascript_file_exists,
        test_pedido_detalhe_template_includes_js,
        test_csrf_token_in_template,
        test_database_models,
        test_api_endpoints_exist,
        test_item_status_fields,
        test_static_files_configuration,
        test_create_test_data,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n✗ EXCEPTION in {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    # Summary
    print_section("SUMMARY")
    passed = sum(results)
    total = len(results)

    print(f"\nTests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total*100):.1f}%")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! The fix should be working correctly.")
        print("\nNext steps:")
        print("1. Start the development server: python manage.py runserver")
        print("2. Login with: 9999 / PIN: 9999")
        print("3. Navigate to the test order")
        print("4. Open browser DevTools (F12) and check Console tab")
        print("5. Try clicking checkboxes to mark items as separated")
        print("6. Verify that:")
        print("   - AJAX requests appear in Network tab")
        print("   - Row color changes to light green")
        print("   - Badge appears showing 'Separado'")
        print("   - Counter updates")
        print("   - Database is updated")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review the errors above.")

    return passed == total


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
