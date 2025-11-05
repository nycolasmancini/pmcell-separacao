"""
Utilitários para cálculo de métricas e tempo útil
"""
from datetime import datetime, timedelta, time
from django.utils import timezone
from django.db.models import Q


def calcular_tempo_util(data_inicio, data_fim):
    """
    Calcula o tempo útil entre duas datas considerando horário comercial.

    Horário comercial: 7:30 - 17:00 (segunda a sexta)

    Args:
        data_inicio: datetime - Data/hora de início
        data_fim: datetime - Data/hora de fim

    Returns:
        timedelta - Tempo útil decorrido
    """
    if not data_inicio or not data_fim:
        return timedelta(0)

    # Garantir que são timezone aware
    if timezone.is_naive(data_inicio):
        data_inicio = timezone.make_aware(data_inicio)
    if timezone.is_naive(data_fim):
        data_fim = timezone.make_aware(data_fim)

    # Se fim antes do início, retorna 0
    if data_fim < data_inicio:
        return timedelta(0)

    # Horário comercial
    HORA_INICIO = time(7, 30)  # 7:30
    HORA_FIM = time(17, 0)     # 17:00
    HORAS_DIA = 9.5            # 9h30min por dia

    tempo_total = timedelta(0)
    dia_atual = data_inicio.date()

    while dia_atual <= data_fim.date():
        # Pular finais de semana (sábado=5, domingo=6)
        if dia_atual.weekday() < 5:  # Segunda a Sexta
            # Determinar início do período para este dia
            if dia_atual == data_inicio.date():
                inicio_periodo = data_inicio.time()
            else:
                inicio_periodo = HORA_INICIO

            # Determinar fim do período para este dia
            if dia_atual == data_fim.date():
                fim_periodo = data_fim.time()
            else:
                fim_periodo = HORA_FIM

            # Ajustar para horário comercial
            if inicio_periodo < HORA_INICIO:
                inicio_periodo = HORA_INICIO
            if fim_periodo > HORA_FIM:
                fim_periodo = HORA_FIM

            # Calcular tempo útil deste dia
            if inicio_periodo < fim_periodo:
                inicio_dt = datetime.combine(dia_atual, inicio_periodo)
                fim_dt = datetime.combine(dia_atual, fim_periodo)
                tempo_total += fim_dt - inicio_dt

        dia_atual += timedelta(days=1)

    return tempo_total


def calcular_metricas_dia():
    """
    Calcula métricas do dia atual para o dashboard.

    Returns:
        dict - {
            'tempo_medio_separacao': timedelta ou None,
            'pedidos_em_aberto': int,
            'total_pedidos_hoje': int
        }
    """
    from apps.core.models import Pedido

    hoje = timezone.localdate()

    # Pedidos finalizados hoje
    finalizados_hoje = Pedido.objects.filter(
        status='FINALIZADO',
        data_finalizacao__date=hoje,
        deletado=False
    )

    # Calcular tempo médio de separação
    tempo_medio = None
    if finalizados_hoje.exists():
        tempos = []
        for pedido in finalizados_hoje:
            if pedido.data_criacao and pedido.data_finalizacao:
                tempo = calcular_tempo_util(pedido.data_criacao, pedido.data_finalizacao)
                tempos.append(tempo.total_seconds())

        if tempos:
            media_segundos = sum(tempos) / len(tempos)
            tempo_medio = timedelta(seconds=media_segundos)

    # Pedidos em aberto (não finalizados e não deletados)
    pedidos_em_aberto = Pedido.objects.filter(
        deletado=False
    ).exclude(
        status__in=['FINALIZADO', 'CANCELADO']
    ).count()

    # Total de pedidos criados hoje
    total_pedidos_hoje = Pedido.objects.filter(
        data_criacao__date=hoje,
        deletado=False
    ).count()

    return {
        'tempo_medio_separacao': tempo_medio,
        'pedidos_em_aberto': pedidos_em_aberto,
        'total_pedidos_hoje': total_pedidos_hoje
    }


def formatar_tempo(tempo_delta):
    """
    Formata um timedelta em string legível.

    Args:
        tempo_delta: timedelta

    Returns:
        str - Formato "Xh Ymin" ou "N/A"
    """
    if not tempo_delta:
        return "N/A"

    total_segundos = int(tempo_delta.total_seconds())
    horas = total_segundos // 3600
    minutos = (total_segundos % 3600) // 60

    if horas > 0:
        return f"{horas}h {minutos}min"
    else:
        return f"{minutos}min"


def calcular_metricas_periodo(data_inicio=None, data_fim=None):
    """
    Calcula métricas de pedidos para um período específico.

    Args:
        data_inicio: date - Data inicial do período (opcional, padrão: 30 dias atrás)
        data_fim: date - Data final do período (opcional, padrão: hoje)

    Returns:
        dict - {
            'total_pedidos': int,
            'pedidos_finalizados': int,
            'pedidos_cancelados': int,
            'taxa_conclusao': float (0-100),
            'tempo_medio_separacao': timedelta ou None,
            'tempo_medio_formatado': str,
            'itens_em_compra_total': int,
            'itens_em_compra_percentual': float (0-100),
            'pedidos_por_status': dict
        }
    """
    from apps.core.models import Pedido, ItemPedido

    # Definir período padrão (últimos 30 dias)
    if not data_fim:
        data_fim = timezone.localdate()
    if not data_inicio:
        data_inicio = data_fim - timedelta(days=30)

    # Query base: pedidos não deletados no período
    pedidos = Pedido.objects.filter(
        data_criacao__date__gte=data_inicio,
        data_criacao__date__lte=data_fim,
        deletado=False
    )

    # Total de pedidos
    total_pedidos = pedidos.count()

    # Pedidos por status
    pedidos_finalizados = pedidos.filter(status='FINALIZADO').count()
    pedidos_cancelados = pedidos.filter(status='CANCELADO').count()

    # Taxa de conclusão (considerando apenas finalizados vs total - cancelados)
    pedidos_validos = total_pedidos - pedidos_cancelados
    taxa_conclusao = (pedidos_finalizados / pedidos_validos * 100) if pedidos_validos > 0 else 0

    # Tempo médio de separação (apenas pedidos finalizados)
    tempo_medio = None
    finalizados_com_tempo = pedidos.filter(
        status='FINALIZADO',
        data_finalizacao__isnull=False
    )

    if finalizados_com_tempo.exists():
        tempos = []
        for pedido in finalizados_com_tempo:
            if pedido.data_criacao and pedido.data_finalizacao:
                tempo = calcular_tempo_util(pedido.data_criacao, pedido.data_finalizacao)
                tempos.append(tempo.total_seconds())

        if tempos:
            media_segundos = sum(tempos) / len(tempos)
            tempo_medio = timedelta(seconds=media_segundos)

    # Itens em compra (considerando todos os pedidos ativos, não apenas do período)
    itens_em_compra = ItemPedido.objects.filter(
        em_compra=True,
        compra_realizada=False,
        pedido__deletado=False
    )
    itens_em_compra_total = itens_em_compra.count()

    # Total de itens de pedidos ativos (não finalizados, não cancelados, não deletados)
    total_itens_ativos = ItemPedido.objects.filter(
        pedido__deletado=False
    ).exclude(
        pedido__status__in=['FINALIZADO', 'CANCELADO']
    ).count()

    itens_em_compra_percentual = (itens_em_compra_total / total_itens_ativos * 100) if total_itens_ativos > 0 else 0

    # Pedidos por status (detalhado)
    pedidos_por_status = {
        'PENDENTE': pedidos.filter(status='PENDENTE').count(),
        'EM_SEPARACAO': pedidos.filter(status='EM_SEPARACAO').count(),
        'AGUARDANDO_COMPRA': pedidos.filter(status='AGUARDANDO_COMPRA').count(),
        'FINALIZADO': pedidos_finalizados,
        'CANCELADO': pedidos_cancelados,
    }

    return {
        'total_pedidos': total_pedidos,
        'pedidos_finalizados': pedidos_finalizados,
        'pedidos_cancelados': pedidos_cancelados,
        'taxa_conclusao': round(taxa_conclusao, 1),
        'tempo_medio_separacao': tempo_medio,
        'tempo_medio_formatado': formatar_tempo(tempo_medio),
        'itens_em_compra_total': itens_em_compra_total,
        'itens_em_compra_percentual': round(itens_em_compra_percentual, 1),
        'pedidos_por_status': pedidos_por_status,
        'periodo': {
            'data_inicio': data_inicio,
            'data_fim': data_fim
        }
    }
