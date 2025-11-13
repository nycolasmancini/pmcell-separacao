"""
Utilitários para validação e otimização de imagens
Usado para upload de imagens personalizadas do empty state
"""

from PIL import Image
from django.core.exceptions import ValidationError
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys


# Constantes de configuração
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB em bytes
MIN_WIDTH = 400
MIN_HEIGHT = 400
TARGET_SIZE = 512  # Largura/altura alvo em pixels
JPEG_QUALITY = 85  # Qualidade de compressão (1-100)
ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.svg']


def validate_image_file(file):
    """
    Valida arquivo de imagem antes do upload

    Validações:
    - Extensão do arquivo (.jpg, .jpeg, .png, .webp, .svg)
    - Tamanho máximo (2 MB)
    - Dimensões mínimas (400x400px) - apenas para imagens raster

    Args:
        file: UploadedFile object do Django

    Raises:
        ValidationError: Se arquivo não atender aos requisitos

    Returns:
        bool: True se validação passou
    """

    # Validar extensão do arquivo
    file_name = file.name.lower()
    file_ext = None
    for ext in ALLOWED_EXTENSIONS:
        if file_name.endswith(ext):
            file_ext = ext
            break

    if not file_ext:
        raise ValidationError(
            f'Formato de arquivo não suportado. '
            f'Use: {", ".join(ALLOWED_EXTENSIONS)}'
        )

    # Validar tamanho do arquivo
    if file.size > MAX_FILE_SIZE:
        size_mb = file.size / (1024 * 1024)
        raise ValidationError(
            f'Arquivo muito grande ({size_mb:.1f} MB). '
            f'Tamanho máximo: {MAX_FILE_SIZE / (1024 * 1024):.0f} MB'
        )

    # SVG não precisa de validação de dimensões (é vetorial)
    if file_ext == '.svg':
        return True

    # Validar dimensões mínimas para imagens raster
    try:
        image = Image.open(file)
        width, height = image.size

        if width < MIN_WIDTH or height < MIN_HEIGHT:
            raise ValidationError(
                f'Imagem muito pequena ({width}x{height}px). '
                f'Dimensões mínimas: {MIN_WIDTH}x{MIN_HEIGHT}px'
            )

        # Validar que é realmente uma imagem
        image.verify()

    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(
            f'Arquivo de imagem inválido ou corrompido: {str(e)}'
        )

    # Reset file pointer após ler
    file.seek(0)

    return True


def optimize_empty_state_image(image_file):
    """
    Otimiza imagem para uso como empty state

    Otimizações aplicadas:
    - Redimensionamento para 512x512px (mantém aspect ratio)
    - Conversão para WebP (exceto SVG)
    - Compressão com 85% de qualidade
    - Remoção de metadados EXIF

    Args:
        image_file: UploadedFile object do Django

    Returns:
        InMemoryUploadedFile: Imagem otimizada pronta para salvar
        None: Se arquivo for SVG (não precisa otimização)
    """

    file_name = image_file.name.lower()

    # SVG não precisa otimização (é vetorial e já é leve)
    if file_name.endswith('.svg'):
        return None

    try:
        # Abrir imagem
        image = Image.open(image_file)

        # Preservar transparência para RGBA/LA, converter P para RGBA
        if image.mode == 'P':
            # Paleta pode ter transparência
            image = image.convert('RGBA')
        elif image.mode not in ('RGB', 'RGBA'):
            # Verificar se tem transparência
            has_transparency = 'transparency' in image.info
            image = image.convert('RGBA' if has_transparency else 'RGB')

        # Redimensionar mantendo aspect ratio
        # Usa thumbnail() que redimensiona até caber no tamanho alvo
        image.thumbnail((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)

        # Salvar em buffer como WebP otimizado
        output = BytesIO()
        image.save(
            output,
            format='WEBP',
            quality=JPEG_QUALITY,
            method=6,  # Método de compressão (0-6, 6 é o mais lento mas melhor)
            optimize=True
        )
        output.seek(0)

        # Criar novo nome de arquivo com extensão .webp
        original_name = image_file.name.rsplit('.', 1)[0]
        new_name = f'{original_name}.webp'

        # Criar InMemoryUploadedFile para retornar
        optimized_file = InMemoryUploadedFile(
            output,
            'ImageField',
            new_name,
            'image/webp',
            sys.getsizeof(output),
            None
        )

        return optimized_file

    except Exception as e:
        raise ValidationError(
            f'Erro ao otimizar imagem: {str(e)}'
        )
