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

    LOGISTICA_CHOICES = [
        ('', 'Selecione...'),
        ('RETIRADA', 'Retirada'),
        ('ENTREGA', 'Entrega'),
        ('TRANSPORTADORA', 'Transportadora'),
        ('MOTOBOY', 'Motoboy'),
    ]

    EMBALAGEM_CHOICES = [
        ('', 'Selecione...'),
        ('CAIXA_PEQUENA', 'Caixa Pequena'),
        ('CAIXA_MEDIA', 'Caixa Média'),
        ('CAIXA_GRANDE', 'Caixa Grande'),
        ('SACO_PLASTICO', 'Saco Plástico'),
        ('SEM_EMBALAGEM', 'Sem Embalagem'),
    ]

    logistica = forms.ChoiceField(
        label='Logística',
        choices=LOGISTICA_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
        })
    )

    embalagem = forms.ChoiceField(
        label='Embalagem',
        choices=EMBALAGEM_CHOICES,
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


# Forms que serão implementados nas próximas fases
# FASE 7: UsuarioForm, EditarUsuarioForm
