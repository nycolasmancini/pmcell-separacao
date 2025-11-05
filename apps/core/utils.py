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
