"""
Módulo para processamento e extração de dados de PDFs de orçamento PMCELL.

Este módulo utiliza pdfplumber para extrair dados estruturados de PDFs de orçamento
no formato padronizado da PMCELL, incluindo informações de cabeçalho e tabela de produtos.
"""

import pdfplumber
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple


class PDFParserError(Exception):
    """Exceção customizada para erros no parser de PDF"""
    pass


def extrair_dados_pdf(pdf_file) -> Dict:
    """
    Extrai dados estruturados de um PDF de orçamento PMCELL.

    Args:
        pdf_file: Arquivo PDF (Django UploadedFile ou caminho)

    Returns:
        Dict contendo:
            - numero_orcamento: str
            - codigo_cliente: str
            - nome_cliente: str
            - data: date
            - produtos: List[Dict] com código, descrição, quantidade, preco_unitario

    Raises:
        PDFParserError: Se houver erro na extração ou validação dos dados
    """
    try:
        with pdfplumber.open(pdf_file) as pdf:
            if not pdf.pages:
                raise PDFParserError("PDF não contém páginas")

            # Processar primeira página (todos os PDFs PMCELL têm 1 página)
            primeira_pagina = pdf.pages[0]
            texto = primeira_pagina.extract_text()

            if not texto:
                raise PDFParserError("Não foi possível extrair texto do PDF")

            # Extrair dados do cabeçalho
            cabecalho = extrair_cabecalho(texto)

            # Extrair tabela de produtos
            produtos = extrair_produtos(primeira_pagina)

            if not produtos:
                raise PDFParserError("Nenhum produto encontrado no PDF")

            return {
                'numero_orcamento': cabecalho['numero_orcamento'],
                'codigo_cliente': cabecalho['codigo_cliente'],
                'nome_cliente': cabecalho['nome_cliente'],
                'data': cabecalho['data'],
                'produtos': produtos
            }

    except Exception as e:
        if isinstance(e, PDFParserError):
            raise
        raise PDFParserError(f"Erro ao processar PDF: {str(e)}")


def extrair_cabecalho(texto: str) -> Dict:
    """
    Extrai informações do cabeçalho do PDF.

    Estrutura esperada:
    - Orçamento Nº: 30912
    - Código: 000015
    - Cliente: NOME DO CLIENTE
    - Data: 04/11/25

    Args:
        texto: Texto extraído do PDF

    Returns:
        Dict com numero_orcamento, codigo_cliente, nome_cliente, data

    Raises:
        PDFParserError: Se campos obrigatórios não forem encontrados
    """
    cabecalho = {}

    # Extrair Número do Orçamento
    match_orcamento = re.search(r'Orçamento\s+Nº:\s*(\d+)', texto, re.IGNORECASE)
    if not match_orcamento:
        raise PDFParserError("Número do orçamento não encontrado no PDF")
    cabecalho['numero_orcamento'] = match_orcamento.group(1).strip()

    # Extrair Código do Cliente
    match_codigo = re.search(r'Código:\s*(\d+)', texto, re.IGNORECASE)
    if not match_codigo:
        raise PDFParserError("Código do cliente não encontrado no PDF")
    cabecalho['codigo_cliente'] = match_codigo.group(1).strip()

    # Extrair Nome do Cliente
    # Padrão: Cliente: NOME (pode terminar com Forma de Pagto:, Vendedor:, ou nova linha)
    match_cliente = re.search(r'Cliente:\s*([A-Z0-9\s\.\-,/()]+?)(?:\s+Forma de Pagto:|Vendedor:|\n)', texto, re.IGNORECASE)
    if not match_cliente:
        raise PDFParserError("Nome do cliente não encontrado no PDF")
    cabecalho['nome_cliente'] = match_cliente.group(1).strip()

    # Extrair Data
    # Formato: DD/MM/YY (ex: 04/11/25)
    match_data = re.search(r'Data:\s*(\d{2}/\d{2}/\d{2})', texto)
    if not match_data:
        raise PDFParserError("Data não encontrada no PDF")

    data_str = match_data.group(1).strip()
    try:
        # Converter DD/MM/YY para date (assumindo 20XX)
        data_obj = datetime.strptime(data_str, '%d/%m/%y').date()
        cabecalho['data'] = data_obj
    except ValueError:
        raise PDFParserError(f"Data inválida no PDF: {data_str}")

    return cabecalho


def extrair_produtos(pagina) -> List[Dict]:
    """
    Extrai produtos da tabela no PDF.

    Estrutura da tabela:
    Código | Produto | Unid. | Quant. | Valor | Total

    Args:
        pagina: Página do pdfplumber

    Returns:
        Lista de dicts com: codigo, descricao, quantidade, preco_unitario

    Raises:
        PDFParserError: Se não conseguir extrair produtos
    """
    produtos = []

    # Extrair tabelas da página
    tabelas = pagina.extract_tables()

    if not tabelas:
        raise PDFParserError("Nenhuma tabela encontrada no PDF")

    # Processar cada tabela encontrada
    for tabela in tabelas:
        if not tabela or len(tabela) < 2:  # Precisa ter header + pelo menos 1 produto
            continue

        # Processar linhas de produtos (pular header)
        for row in tabela[1:]:
            if not row:
                continue

            # Se row tem apenas 1 coluna (tudo numa string), fazer split
            if len(row) == 1 and isinstance(row[0], str):
                linha_texto = row[0].strip()

                # Ignorar linhas de totais/rodapé
                if any(palavra in linha_texto.upper() for palavra in ['VALOR TOTAL', 'DESCONTO', 'VALOR A PAGAR', 'PÁGINA']):
                    continue

                # Fazer parsing da linha (formato: código descricao unid quant valor total)
                # Regex para extrair: código (5 dígitos) no início
                match = re.match(r'^(\d{5})\s+(.+?)\s+(UN|PC|CX|KG|MT|LT)?\s+(\d+(?:,\d{2})?)\s+(\d+,\d{2})\s+(\d+,\d{2})$', linha_texto)

                if match:
                    codigo = match.group(1)
                    descricao = match.group(2).strip()
                    quantidade_str = match.group(4).replace(',', '.')
                    preco_str = match.group(5).replace(',', '.')

                    try:
                        produto = {
                            'codigo': codigo,
                            'descricao': descricao,
                            'quantidade': Decimal(quantidade_str),
                            'preco_unitario': Decimal(preco_str)
                        }
                        produtos.append(produto)
                    except (InvalidOperation, ValueError) as e:
                        print(f"Aviso: Erro ao processar linha '{linha_texto}': {str(e)}")
                        continue
            else:
                # Tentar processar como lista de células
                row = [str(cell).strip() if cell else '' for cell in row]

                # Ignorar linhas de totais/rodapé
                primeiro_campo = row[0].upper() if row else ''
                if any(palavra in primeiro_campo for palavra in ['VALOR', 'DESCONTO', 'TOTAL', 'PAGAR', 'PÁGINA']):
                    continue

                try:
                    produto = processar_linha_produto(row)
                    if produto:
                        produtos.append(produto)
                except Exception as e:
                    print(f"Aviso: Erro ao processar linha {row}: {str(e)}")
                    continue

    return produtos


def processar_linha_produto(row: List[str]) -> Optional[Dict]:
    """
    Processa uma linha da tabela de produtos.

    Args:
        row: Lista com células da linha [código, produto, unid, quant, valor, total]

    Returns:
        Dict com codigo, descricao, quantidade, preco_unitario ou None se inválida
    """
    if len(row) < 4:
        return None

    codigo = row[0].strip()
    descricao = row[1].strip()

    # Código deve ser numérico (pode ter 5 dígitos)
    if not codigo or not codigo.isdigit():
        return None

    # Descrição não pode estar vazia
    if not descricao:
        return None

    # Encontrar quantidade e preço
    # Estrutura: [código, produto, unid, quant, valor, total]
    # Mas "unid" pode estar vazia, então precisamos ser flexíveis

    # Tentar identificar quantidade e preço pelos últimos campos numéricos
    campos_numericos = []
    for i in range(2, len(row)):
        campo = limpar_numero(row[i])
        if campo:
            try:
                valor_decimal = Decimal(campo)
                campos_numericos.append(valor_decimal)
            except (InvalidOperation, ValueError):
                continue

    # Precisa de pelo menos quantidade e preço unitário
    if len(campos_numericos) < 2:
        return None

    # A quantidade é o primeiro número, o preço unitário é o segundo
    quantidade = campos_numericos[0]
    preco_unitario = campos_numericos[1]

    # Validações
    if quantidade <= 0 or preco_unitario <= 0:
        return None

    return {
        'codigo': codigo,
        'descricao': descricao,
        'quantidade': quantidade,
        'preco_unitario': preco_unitario
    }


def limpar_numero(valor: str) -> Optional[str]:
    """
    Limpa e normaliza string numérica (remove R$, espaços, substitui vírgula por ponto).

    Args:
        valor: String com número

    Returns:
        String normalizada ou None se inválida
    """
    if not valor:
        return None

    # Remover R$, espaços, pontos de milhares
    valor = valor.replace('R$', '').replace(' ', '').strip()

    # Substituir vírgula decimal por ponto
    # Detectar se vírgula é decimal (último separador) ou milhares
    if ',' in valor:
        partes = valor.split(',')
        if len(partes) == 2 and len(partes[1]) <= 2:
            # É decimal: 3.350,00 ou 1,00
            valor = valor.replace('.', '').replace(',', '.')
        else:
            # É milhares, remover
            valor = valor.replace(',', '')
    else:
        # Remover pontos de milhares se houver
        if valor.count('.') > 1:
            valor = valor.replace('.', '')

    # Validar se é número válido
    try:
        float(valor)
        return valor
    except ValueError:
        return None


def validar_orcamento(dados: Dict) -> Tuple[bool, Optional[str]]:
    """
    Valida dados extraídos do PDF.

    Args:
        dados: Dict com dados extraídos

    Returns:
        (valido: bool, erro: Optional[str])
    """
    # Validar número do orçamento
    if not dados.get('numero_orcamento'):
        return False, "Número do orçamento não encontrado"

    if not dados['numero_orcamento'].isdigit():
        return False, f"Número do orçamento inválido: {dados['numero_orcamento']}"

    # Validar código do cliente
    if not dados.get('codigo_cliente'):
        return False, "Código do cliente não encontrado"

    # Validar nome do cliente
    if not dados.get('nome_cliente'):
        return False, "Nome do cliente não encontrado"

    if len(dados['nome_cliente']) < 2:
        return False, "Nome do cliente inválido"

    # Validar data
    if not dados.get('data'):
        return False, "Data não encontrada"

    # Validar produtos
    if not dados.get('produtos') or len(dados['produtos']) == 0:
        return False, "Nenhum produto encontrado no orçamento"

    # Validar cada produto
    for i, produto in enumerate(dados['produtos'], 1):
        if not produto.get('codigo'):
            return False, f"Produto {i}: código não encontrado"

        if not produto.get('descricao'):
            return False, f"Produto {i}: descrição não encontrada"

        if not produto.get('quantidade') or produto['quantidade'] <= 0:
            return False, f"Produto {i}: quantidade inválida"

        if not produto.get('preco_unitario') or produto['preco_unitario'] <= 0:
            return False, f"Produto {i}: preço unitário inválido"

    return True, None
