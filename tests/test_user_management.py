"""
Testes para Gestão de Usuários - FASE 7
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pmcell_settings.settings')
django.setup()

from django.test import TestCase, Client
from apps.core.models import Usuario, LogAuditoria
from apps.core.forms import CriarUsuarioForm, EditarUsuarioForm, ResetarPinForm


class TestUserManagementForms(TestCase):
    """Testes para os formulários de gestão de usuários"""

    def setUp(self):
        """Setup inicial para os testes"""
        # Usar o admin criado pela migration (numero_login=1000)
        self.admin = Usuario.objects.get(numero_login=1000)

    def test_criar_usuario_form_valido(self):
        """Teste: formulário válido para criar usuário"""
        form_data = {
            'numero_login': 1001,
            'nome': 'Vendedor Teste',
            'tipo': 'VENDEDOR',
            'pin': '5678',
            'pin_confirmacao': '5678'
        }
        form = CriarUsuarioForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_criar_usuario_form_numero_duplicado(self):
        """Teste: não deve aceitar número de login duplicado"""
        form_data = {
            'numero_login': 1000,  # Mesmo número do admin
            'nome': 'Vendedor Teste',
            'tipo': 'VENDEDOR',
            'pin': '5678',
            'pin_confirmacao': '5678'
        }
        form = CriarUsuarioForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('numero_login', form.errors)

    def test_criar_usuario_form_pin_nao_confere(self):
        """Teste: PINs devem ser iguais"""
        form_data = {
            'numero_login': 1001,
            'nome': 'Vendedor Teste',
            'tipo': 'VENDEDOR',
            'pin': '5678',
            'pin_confirmacao': '1234'  # Diferente
        }
        form = CriarUsuarioForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)

    def test_criar_usuario_form_pin_nao_numerico(self):
        """Teste: PIN deve ser numérico"""
        form_data = {
            'numero_login': 1001,
            'nome': 'Vendedor Teste',
            'tipo': 'VENDEDOR',
            'pin': 'abcd',  # Não numérico
            'pin_confirmacao': 'abcd'
        }
        form = CriarUsuarioForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('pin', form.errors)

    def test_editar_usuario_form_valido(self):
        """Teste: formulário válido para editar usuário"""
        form_data = {
            'nome': 'Admin Atualizado',
            'tipo': 'ADMINISTRADOR',
            'ativo': True
        }
        form = EditarUsuarioForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_resetar_pin_form_valido(self):
        """Teste: formulário válido para resetar PIN"""
        form_data = {
            'pin': '9999',
            'pin_confirmacao': '9999'
        }
        form = ResetarPinForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_resetar_pin_form_pin_nao_confere(self):
        """Teste: PINs devem ser iguais no reset"""
        form_data = {
            'pin': '9999',
            'pin_confirmacao': '8888'
        }
        form = ResetarPinForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)


class TestUserManagementViews(TestCase):
    """Testes para as views de gestão de usuários"""

    def setUp(self):
        """Setup inicial para os testes"""
        # Usar o admin criado pela migration (numero_login=1000)
        self.admin = Usuario.objects.get(numero_login=1000)

        # Criar vendedor
        self.vendedor = Usuario.objects.create(
            numero_login=2000,
            nome='Vendedor Teste',
            tipo='VENDEDOR',
            ativo=True
        )
        self.vendedor.set_pin('5678')
        self.vendedor.save()

        self.client = Client()

    def test_lista_usuarios_requer_login(self):
        """Teste: lista de usuários requer login"""
        response = self.client.get('/usuarios/')
        self.assertEqual(response.status_code, 302)  # Redirect para login

    def test_lista_usuarios_requer_admin(self):
        """Teste: lista de usuários requer ser admin"""
        # Login como vendedor
        self.client.post('/login/', {
            'numero_login': '2000',
            'pin': '5678'
        })
        response = self.client.get('/usuarios/')
        self.assertEqual(response.status_code, 302)  # Redirect (não autorizado)

    def test_lista_usuarios_admin_pode_acessar(self):
        """Teste: admin pode acessar lista de usuários"""
        # Login como admin
        self.client.post('/login/', {
            'numero_login': '1000',
            'pin': '1234'
        })
        response = self.client.get('/usuarios/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('usuarios', response.context)

    def test_criar_usuario_admin(self):
        """Teste: admin pode criar usuário"""
        # Login como admin
        self.client.post('/login/', {
            'numero_login': '1000',
            'pin': '1234'
        })

        # Criar usuário
        response = self.client.post('/usuarios/criar/', {
            'numero_login': '3000',
            'nome': 'Separador Teste',
            'tipo': 'SEPARADOR',
            'pin': '9999',
            'pin_confirmacao': '9999'
        })

        # Deve redirecionar para lista de usuários
        self.assertEqual(response.status_code, 302)

        # Verificar se usuário foi criado
        usuario = Usuario.objects.filter(numero_login=3000).first()
        self.assertIsNotNone(usuario)
        self.assertEqual(usuario.nome, 'Separador Teste')
        self.assertEqual(usuario.tipo, 'SEPARADOR')
        self.assertTrue(usuario.ativo)

    def test_editar_usuario_admin(self):
        """Teste: admin pode editar usuário"""
        # Login como admin
        self.client.post('/login/', {
            'numero_login': '1000',
            'pin': '1234'
        })

        # Editar vendedor
        response = self.client.post(f'/usuarios/{self.vendedor.id}/editar/', {
            'nome': 'Vendedor Atualizado',
            'tipo': 'VENDEDOR',
            'ativo': True
        })

        # Deve redirecionar para lista de usuários
        self.assertEqual(response.status_code, 302)

        # Verificar se usuário foi atualizado
        self.vendedor.refresh_from_db()
        self.assertEqual(self.vendedor.nome, 'Vendedor Atualizado')

    def test_resetar_pin_admin(self):
        """Teste: admin pode resetar PIN de usuário"""
        # Login como admin
        self.client.post('/login/', {
            'numero_login': '1000',
            'pin': '1234'
        })

        # Resetar PIN do vendedor
        response = self.client.post(f'/usuarios/{self.vendedor.id}/resetar-pin/', {
            'pin': '7777',
            'pin_confirmacao': '7777'
        })

        # Deve redirecionar para lista de usuários
        self.assertEqual(response.status_code, 302)

        # Verificar se PIN foi alterado
        self.vendedor.refresh_from_db()
        self.assertTrue(self.vendedor.check_pin('7777'))
        self.assertFalse(self.vendedor.check_pin('5678'))  # PIN antigo não funciona mais

    def test_desativar_usuario_admin(self):
        """Teste: admin pode desativar usuário"""
        # Login como admin
        self.client.post('/login/', {
            'numero_login': '1000',
            'pin': '1234'
        })

        # Desativar vendedor
        response = self.client.post(f'/usuarios/{self.vendedor.id}/toggle-ativo/')

        # Deve redirecionar para lista de usuários
        self.assertEqual(response.status_code, 302)

        # Verificar se usuário foi desativado
        self.vendedor.refresh_from_db()
        self.assertFalse(self.vendedor.ativo)

    def test_usuario_inativo_nao_pode_fazer_login(self):
        """Teste: usuário inativo não pode fazer login"""
        # Desativar vendedor
        self.vendedor.ativo = False
        self.vendedor.save()

        # Tentar fazer login
        response = self.client.post('/login/', {
            'numero_login': '2000',
            'pin': '5678'
        })

        # Não deve fazer login (permanece na tela de login)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Usuário inativo')


def run_tests():
    """Executa os testes"""
    from django.test.utils import get_runner
    from django.conf import settings

    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False, keepdb=False)

    # Executar testes
    failures = test_runner.run_tests(['tests.test_user_management'])

    return failures == 0


if __name__ == '__main__':
    print("=" * 80)
    print("TESTES - GESTÃO DE USUÁRIOS (FASE 7)")
    print("=" * 80)
    print()

    success = run_tests()

    print()
    print("=" * 80)
    if success:
        print("✅ TODOS OS TESTES PASSARAM!")
    else:
        print("❌ ALGUNS TESTES FALHARAM")
    print("=" * 80)

    sys.exit(0 if success else 1)
