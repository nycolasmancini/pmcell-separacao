from django import forms
from .models import Usuario, Pedido, ItemPedido
from django.core.validators import FileExtensionValidator


# =====================
# FASE 3: Upload de PDF
# =====================

class UploadPDFForm(forms.Form):
    """Formulário para upload de arquivo PDF"""
    arquivo_pdf = forms.FileField(
        label='Arquivo PDF',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        widget=forms.FileInput(attrs={
            'accept': '.pdf',
            'class': 'hidden',
            'id': 'pdf-file-input'
        }),
        help_text='Tamanho máximo: 10MB'
    )

    def clean_arquivo_pdf(self):
        """Valida o arquivo PDF"""
        arquivo = self.cleaned_data.get('arquivo_pdf')

        if not arquivo:
            raise forms.ValidationError('Nenhum arquivo foi selecionado.')

        # Validar tamanho (10MB = 10 * 1024 * 1024 bytes)
        max_size = 10 * 1024 * 1024
        if arquivo.size > max_size:
            raise forms.ValidationError(f'Arquivo muito grande. Tamanho máximo: 10MB.')

        # Validar tipo MIME
        if arquivo.content_type != 'application/pdf':
            raise forms.ValidationError('Arquivo deve ser um PDF válido.')

        return arquivo


class ConfirmarPedidoForm(forms.Form):
    """Formulário para confirmar pedido após processamento do PDF"""

    logistica = forms.ChoiceField(
        label='Logística',
        choices=[('', 'Selecione...')] + Pedido.LOGISTICA_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
        })
    )

    embalagem = forms.ChoiceField(
        label='Embalagem',
        choices=[('', 'Selecione...')] + Pedido.EMBALAGEM_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
        })
    )

    observacoes = forms.CharField(
        label='Observações',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'rows': 3,
            'placeholder': 'Observações adicionais sobre o pedido (opcional)'
        })
    )

    def clean_logistica(self):
        """Valida o campo logística"""
        logistica = self.cleaned_data.get('logistica')
        if not logistica:
            raise forms.ValidationError('Selecione uma opção de logística.')
        return logistica

    def clean_embalagem(self):
        """Valida o campo embalagem"""
        embalagem = self.cleaned_data.get('embalagem')
        if not embalagem:
            raise forms.ValidationError('Selecione uma opção de embalagem.')
        return embalagem


# =====================
# FASE 5: Separação de Pedidos
# =====================

class SubstituirProdutoForm(forms.Form):
    """Formulário para substituir produto em um item do pedido"""
    produto_substituto = forms.CharField(
        label='Produto Substituto',
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Ex: Produto ABC ou Código 12345'
        }),
        help_text='Informe o código ou descrição do produto que foi usado no lugar'
    )

    def clean_produto_substituto(self):
        """Valida o campo produto_substituto"""
        produto_substituto = self.cleaned_data.get('produto_substituto')
        if not produto_substituto or not produto_substituto.strip():
            raise forms.ValidationError('Informe o produto substituto.')
        return produto_substituto.strip()


class MarcarCompraForm(forms.Form):
    """Formulário para marcar item(s) para compra"""
    outros_pedidos = forms.MultipleChoiceField(
        label='Marcar também em outros pedidos',
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-checkbox h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500'
        }),
        help_text='Selecione outros pedidos onde o mesmo produto deve ser marcado para compra'
    )

    def __init__(self, *args, **kwargs):
        outros_itens = kwargs.pop('outros_itens', [])
        super().__init__(*args, **kwargs)

        # Criar choices com os outros itens
        if outros_itens:
            choices = [
                (str(item.id), f"Pedido {item.pedido.numero_orcamento} - {item.produto.descricao[:50]} (Qtd: {item.quantidade_solicitada})")
                for item in outros_itens
            ]
            self.fields['outros_pedidos'].choices = choices


# =====================
# FASE 7: Gestão de Usuários
# =====================

class CriarUsuarioForm(forms.Form):
    """Formulário para criar novo usuário"""

    TIPO_CHOICES = [
        ('', 'Selecione...'),
        ('VENDEDOR', 'Vendedor'),
        ('SEPARADOR', 'Separador'),
        ('COMPRADORA', 'Compradora'),
        ('ADMINISTRADOR', 'Administrador'),
    ]

    numero_login = forms.IntegerField(
        label='Número de Login',
        min_value=1000,
        max_value=9999,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': '1000-9999'
        }),
        help_text='Número de 4 dígitos único para login'
    )

    nome = forms.CharField(
        label='Nome Completo',
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Nome completo do usuário'
        })
    )

    tipo = forms.ChoiceField(
        label='Tipo de Usuário',
        choices=TIPO_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
        })
    )

    pin = forms.CharField(
        label='PIN',
        min_length=4,
        max_length=4,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': '****'
        }),
        help_text='PIN de 4 dígitos numéricos'
    )

    pin_confirmacao = forms.CharField(
        label='Confirmar PIN',
        min_length=4,
        max_length=4,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': '****'
        })
    )

    def clean_numero_login(self):
        """Valida se o número de login é único"""
        numero_login = self.cleaned_data.get('numero_login')

        if Usuario.objects.filter(numero_login=numero_login).exists():
            raise forms.ValidationError(f'Número de login {numero_login} já está em uso.')

        return numero_login

    def clean_pin(self):
        """Valida se o PIN contém apenas dígitos"""
        pin = self.cleaned_data.get('pin')

        if not pin.isdigit():
            raise forms.ValidationError('PIN deve conter apenas números.')

        if len(pin) != 4:
            raise forms.ValidationError('PIN deve ter exatamente 4 dígitos.')

        return pin

    def clean(self):
        """Valida se os PINs conferem"""
        cleaned_data = super().clean()
        pin = cleaned_data.get('pin')
        pin_confirmacao = cleaned_data.get('pin_confirmacao')

        if pin and pin_confirmacao and pin != pin_confirmacao:
            raise forms.ValidationError('Os PINs não conferem.')

        return cleaned_data

    def clean_tipo(self):
        """Valida o tipo de usuário"""
        tipo = self.cleaned_data.get('tipo')
        if not tipo:
            raise forms.ValidationError('Selecione o tipo de usuário.')
        return tipo


class EditarUsuarioForm(forms.Form):
    """Formulário para editar usuário existente"""

    TIPO_CHOICES = [
        ('VENDEDOR', 'Vendedor'),
        ('SEPARADOR', 'Separador'),
        ('COMPRADORA', 'Compradora'),
        ('ADMINISTRADOR', 'Administrador'),
    ]

    nome = forms.CharField(
        label='Nome Completo',
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
        })
    )

    tipo = forms.ChoiceField(
        label='Tipo de Usuário',
        choices=TIPO_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
        })
    )

    ativo = forms.BooleanField(
        label='Usuário Ativo',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500'
        }),
        help_text='Desmarque para desativar o usuário (bloquear login e ocultar das listas)'
    )


class ResetarPinForm(forms.Form):
    """Formulário para resetar PIN de usuário"""

    pin = forms.CharField(
        label='Novo PIN',
        min_length=4,
        max_length=4,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': '****'
        }),
        help_text='PIN de 4 dígitos numéricos'
    )

    pin_confirmacao = forms.CharField(
        label='Confirmar Novo PIN',
        min_length=4,
        max_length=4,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': '****'
        })
    )

    def clean_pin(self):
        """Valida se o PIN contém apenas dígitos"""
        pin = self.cleaned_data.get('pin')

        if not pin.isdigit():
            raise forms.ValidationError('PIN deve conter apenas números.')

        if len(pin) != 4:
            raise forms.ValidationError('PIN deve ter exatamente 4 dígitos.')

        return pin

    def clean(self):
        """Valida se os PINs conferem"""
        cleaned_data = super().clean()
        pin = cleaned_data.get('pin')
        pin_confirmacao = cleaned_data.get('pin_confirmacao')

        if pin and pin_confirmacao and pin != pin_confirmacao:
            raise forms.ValidationError('Os PINs não conferem.')

        return cleaned_data


# =====================
# FASE 8: Histórico e Métricas
# =====================

class HistoricoFiltrosForm(forms.Form):
    """Formulário para filtrar histórico de pedidos"""

    STATUS_CHOICES = [
        ('', 'Todos os Status'),
        ('PENDENTE', 'Pendente'),
        ('EM_SEPARACAO', 'Em Separação'),
        ('AGUARDANDO_COMPRA', 'Aguardando Compra'),
        ('FINALIZADO', 'Finalizado'),
        ('CANCELADO', 'Cancelado'),
    ]

    data_inicio = forms.DateField(
        label='Data Início',
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
        }),
        help_text='Data inicial do período'
    )

    data_fim = forms.DateField(
        label='Data Fim',
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
        }),
        help_text='Data final do período'
    )

    vendedor = forms.ChoiceField(
        label='Vendedor',
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
        }),
        help_text='Filtrar por vendedor específico'
    )

    status = forms.ChoiceField(
        label='Status',
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Carregar vendedores ativos para o dropdown
        vendedores = Usuario.objects.filter(
            tipo='VENDEDOR',
            ativo=True
        ).order_by('nome')

        vendedor_choices = [('', 'Todos os Vendedores')]
        vendedor_choices.extend([
            (str(v.id), f"{v.nome} ({v.numero_login})")
            for v in vendedores
        ])

        self.fields['vendedor'].choices = vendedor_choices

    def clean(self):
        """Valida o período de datas"""
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')

        if data_inicio and data_fim and data_inicio > data_fim:
            raise forms.ValidationError('Data de início não pode ser posterior à data de fim.')

        return cleaned_data
