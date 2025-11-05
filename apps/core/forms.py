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


# Forms que serão implementados nas próximas fases
# FASE 7: UsuarioForm, EditarUsuarioForm
