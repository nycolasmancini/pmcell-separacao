"""
Testes para Histórico e Métricas - FASE 8
"""
import os
import sys
import django
from datetime import timedelta

# Setup Django
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pmcell_settings.settings')
django.setup()

from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse
from apps.core.models import Usuario, Pedido, ItemPedido, Produto
from apps.core.forms import HistoricoFiltrosForm
from apps.core.utils import calcular_metricas_periodo


class TestHistoricoFiltrosForm(TestCase):
    """Testes para o formulário de filtros de histórico"""

    def setUp(self):
        """Setup inicial para os testes"""
        # Criar vendedor para os testes
        self.vendedor = Usuario.objects.create_user(
            numero_login=2001,
            nome='Vendedor Teste',
            tipo='VENDEDOR',
            pin='1234'
        )

    def test_form_sem_filtros(self):
        """Teste: formulário válido sem filtros"""
        form = HistoricoFiltrosForm(data={})
        self.assertTrue(form.is_valid())

    def test_form_com_periodo_valido(self):
        """Teste: formulário válido com período"""
        hoje = timezone.localdate()
        ontem = hoje - timedelta(days=1)

        form_data = {
            'data_inicio': ontem,
            'data_fim': hoje
        }
        form = HistoricoFiltrosForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_form_periodo_invalido(self):
        """Teste: data de início posterior à data fim"""
        hoje = timezone.localdate()
        amanha = hoje + timedelta(days=1)

        form_data = {
            'data_inicio': amanha,
            'data_fim': hoje
        }
        form = HistoricoFiltrosForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_form_vendedor_choices(self):
        """Teste: vendedor dropdown contém vendedores ativos"""
        form = HistoricoFiltrosForm()
        vendedor_choices = dict(form.fields['vendedor'].choices)

        # Deve conter opção "Todos"
        self.assertIn('', vendedor_choices)

        # Deve conter o vendedor criado
        self.assertTrue(
            any(str(self.vendedor.id) in key for key in vendedor_choices.keys())
        )


class TestHistoricoView(TestCase):
    """Testes para a view de histórico"""

    def setUp(self):
        """Setup inicial para os testes"""
        self.client = Client()

        # Pegar ou criar admin
        self.admin, _ = Usuario.objects.get_or_create(
            numero_login=1000,
            defaults={
                'nome': 'Admin',
                'tipo': 'ADMINISTRADOR'
            }
        )
        if not self.admin.pin_hash:
            self.admin.set_pin('1234')
            self.admin.save()

        # Criar vendedor
        self.vendedor = Usuario.objects.create_user(
            numero_login=2001,
            nome='Vendedor Teste',
            tipo='VENDEDOR',
            pin='1234'
        )

        # Criar produto
        self.produto = Produto.objects.create(
            codigo='PROD001',
            descricao='Produto Teste'
        )

        # Criar pedidos
        self.pedido1 = Pedido.objects.create(
            numero_orcamento='ORC-001',
            codigo_cliente='CLI-001',
            nome_cliente='Cliente 1',
            vendedor=self.vendedor,
            data=timezone.localdate(),
            logistica='RETIRADA',
            embalagem='CAIXA_MEDIA',
            status='PENDENTE'
        )

        self.pedido2 = Pedido.objects.create(
            numero_orcamento='ORC-002',
            codigo_cliente='CLI-002',
            nome_cliente='Cliente 2',
            vendedor=self.vendedor,
            data=timezone.localdate(),
            logistica='ENTREGA',
            embalagem='CAIXA_GRANDE',
            status='FINALIZADO'
        )

        # Login
        self.client.post(reverse('login'), {
            'numero_login': '1000',
            'pin': '1234'
        })

    def test_historico_view_acesso(self):
        """Teste: view de histórico acessível por usuário logado"""
        response = self.client.get(reverse('historico'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Histórico de Pedidos')

    def test_historico_view_sem_login(self):
        """Teste: view redireciona para login se não autenticado"""
        self.client.logout()
        response = self.client.get(reverse('historico'))
        self.assertEqual(response.status_code, 302)  # Redirect

    def test_historico_view_lista_pedidos(self):
        """Teste: view lista pedidos ativos"""
        response = self.client.get(reverse('historico'))
        self.assertContains(response, 'ORC-001')
        self.assertContains(response, 'ORC-002')

    def test_historico_view_nao_lista_deletados(self):
        """Teste: view não lista pedidos deletados"""
        # Deletar pedido
        self.pedido1.deletado = True
        self.pedido1.save()

        response = self.client.get(reverse('historico'))
        self.assertNotContains(response, 'ORC-001')
        self.assertContains(response, 'ORC-002')

    def test_historico_view_filtro_status(self):
        """Teste: filtro por status funciona"""
        response = self.client.get(reverse('historico'), {'status': 'FINALIZADO'})
        self.assertNotContains(response, 'ORC-001')
        self.assertContains(response, 'ORC-002')

    def test_historico_view_paginacao(self):
        """Teste: paginação funciona corretamente"""
        # Criar 25 pedidos (mais que o limite de 20 por página)
        for i in range(3, 28):
            Pedido.objects.create(
                numero_orcamento=f'ORC-{i:03d}',
                codigo_cliente=f'CLI-{i:03d}',
                nome_cliente=f'Cliente {i}',
                vendedor=self.vendedor,
                data=timezone.localdate(),
                logistica='RETIRADA',
                embalagem='CAIXA_MEDIA',
                status='PENDENTE'
            )

        # Primeira página
        response = self.client.get(reverse('historico'))
        self.assertContains(response, 'Próxima')

        # Segunda página
        response = self.client.get(reverse('historico'), {'page': 2})
        self.assertContains(response, 'Anterior')


class TestMetricasUtils(TestCase):
    """Testes para as funções de cálculo de métricas"""

    def setUp(self):
        """Setup inicial para os testes"""
        # Criar vendedor
        self.vendedor = Usuario.objects.create_user(
            numero_login=2001,
            nome='Vendedor Teste',
            tipo='VENDEDOR',
            pin='1234'
        )

        # Criar produto
        self.produto = Produto.objects.create(
            codigo='PROD001',
            descricao='Produto Teste'
        )

    def test_calcular_metricas_sem_pedidos(self):
        """Teste: métricas com zero pedidos"""
        metricas = calcular_metricas_periodo()

        self.assertEqual(metricas['total_pedidos'], 0)
        self.assertEqual(metricas['pedidos_finalizados'], 0)
        self.assertEqual(metricas['taxa_conclusao'], 0)
        self.assertIsNone(metricas['tempo_medio_separacao'])

    def test_calcular_metricas_com_pedidos(self):
        """Teste: métricas com pedidos criados"""
        # Criar pedidos
        Pedido.objects.create(
            numero_orcamento='ORC-001',
            codigo_cliente='CLI-001',
            nome_cliente='Cliente 1',
            vendedor=self.vendedor,
            data=timezone.localdate(),
            logistica='RETIRADA',
            embalagem='CAIXA_MEDIA',
            status='FINALIZADO',
            data_finalizacao=timezone.now()
        )

        Pedido.objects.create(
            numero_orcamento='ORC-002',
            codigo_cliente='CLI-002',
            nome_cliente='Cliente 2',
            vendedor=self.vendedor,
            data=timezone.localdate(),
            logistica='ENTREGA',
            embalagem='CAIXA_GRANDE',
            status='PENDENTE'
        )

        metricas = calcular_metricas_periodo()

        self.assertEqual(metricas['total_pedidos'], 2)
        self.assertEqual(metricas['pedidos_finalizados'], 1)
        self.assertEqual(metricas['taxa_conclusao'], 50.0)


class TestMetricasView(TestCase):
    """Testes para a view de métricas"""

    def setUp(self):
        """Setup inicial para os testes"""
        self.client = Client()

        # Pegar ou criar admin
        self.admin, _ = Usuario.objects.get_or_create(
            numero_login=1000,
            defaults={
                'nome': 'Admin',
                'tipo': 'ADMINISTRADOR'
            }
        )
        if not self.admin.pin_hash:
            self.admin.set_pin('1234')
            self.admin.save()

        # Login
        self.client.post(reverse('login'), {
            'numero_login': '1000',
            'pin': '1234'
        })

    def test_metricas_view_acesso(self):
        """Teste: view de métricas acessível por usuário logado"""
        response = self.client.get(reverse('metricas'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Métricas de Performance')

    def test_metricas_view_sem_login(self):
        """Teste: view redireciona para login se não autenticado"""
        self.client.logout()
        response = self.client.get(reverse('metricas'))
        self.assertEqual(response.status_code, 302)  # Redirect

    def test_metricas_view_mostra_indicadores(self):
        """Teste: view mostra cards de indicadores"""
        response = self.client.get(reverse('metricas'))
        self.assertContains(response, 'Total de Pedidos')
        self.assertContains(response, 'Taxa de Conclusão')
        self.assertContains(response, 'Tempo Médio Separação')
        self.assertContains(response, 'Itens Aguardando Compra')

    def test_metricas_view_atualizar_post(self):
        """Teste: botão atualizar métricas (POST) funciona"""
        response = self.client.post(reverse('metricas'), {
            'periodo': '7'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Métricas atualizadas com sucesso')


if __name__ == '__main__':
    import unittest
    unittest.main()
