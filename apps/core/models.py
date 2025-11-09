from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password as django_check_password


class UsuarioManager(BaseUserManager):
    """Manager customizado para o modelo Usuario"""

    def create_user(self, numero_login, nome, tipo, pin, **extra_fields):
        """Cria e salva um Usuario regular"""
        if not numero_login:
            raise ValueError('O número de login é obrigatório')
        if not nome:
            raise ValueError('O nome é obrigatório')
        if not tipo:
            raise ValueError('O tipo de usuário é obrigatório')
        if not pin:
            raise ValueError('O PIN é obrigatório')

        # Validar número de login (4 dígitos)
        if not (1000 <= numero_login <= 9999):
            raise ValueError('O número de login deve ter 4 dígitos (1000-9999)')

        # Validar PIN (4 dígitos)
        if not (isinstance(pin, str) and len(pin) == 4 and pin.isdigit()):
            raise ValueError('O PIN deve ter 4 dígitos numéricos')

        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)

        user = self.model(
            numero_login=numero_login,
            nome=nome,
            tipo=tipo,
            **extra_fields
        )
        user.set_pin(pin)
        user.save(using=self._db)
        return user

    def create_superuser(self, numero_login, nome, tipo, pin, **extra_fields):
        """Cria e salva um superusuário"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('tipo', 'ADMINISTRADOR')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser deve ter is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser deve ter is_superuser=True.')

        return self.create_user(numero_login, nome, tipo, pin, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Modelo customizado de usuário com autenticação por número de login e PIN"""

    TIPO_CHOICES = [
        ('VENDEDOR', 'Vendedor'),
        ('SEPARADOR', 'Separador'),
        ('COMPRADORA', 'Compradora'),
        ('ADMINISTRADOR', 'Administrador'),
    ]

    numero_login = models.IntegerField(
        unique=True,
        validators=[MinValueValidator(1000), MaxValueValidator(9999)],
        verbose_name='Número de Login'
    )
    nome = models.CharField(max_length=200, verbose_name='Nome')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name='Tipo')
    pin_hash = models.CharField(max_length=128, verbose_name='PIN Hash')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    ultimo_acesso = models.DateTimeField(null=True, blank=True, verbose_name='Último Acesso')
    tentativas_login = models.IntegerField(default=0, verbose_name='Tentativas de Login')
    bloqueado_ate = models.DateTimeField(null=True, blank=True, verbose_name='Bloqueado Até')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    # Campos necessários para integração com Django admin
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = 'numero_login'
    REQUIRED_FIELDS = ['nome', 'tipo']

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        ordering = ['numero_login']

    def __str__(self):
        return f"{self.numero_login} - {self.nome}"

    def set_pin(self, raw_pin):
        """Define o PIN do usuário (armazena como hash)"""
        if not (isinstance(raw_pin, str) and len(raw_pin) == 4 and raw_pin.isdigit()):
            raise ValueError('O PIN deve ter 4 dígitos numéricos')
        self.pin_hash = make_password(raw_pin)

    def check_pin(self, raw_pin):
        """Verifica se o PIN fornecido está correto"""
        return django_check_password(raw_pin, self.pin_hash)

    def pode_fazer_login(self):
        """Verifica se o usuário pode fazer login"""
        if not self.ativo:
            return False, 'Usuário inativo'

        if self.bloqueado_ate and timezone.now() < self.bloqueado_ate:
            return False, f'Usuário bloqueado até {self.bloqueado_ate.strftime("%d/%m/%Y %H:%M")}'

        # Se passou o período de bloqueio, limpa o bloqueio
        if self.bloqueado_ate and timezone.now() >= self.bloqueado_ate:
            self.bloqueado_ate = None
            self.tentativas_login = 0
            self.save()

        return True, 'OK'

    def registrar_tentativa_login(self, sucesso=False):
        """Registra tentativa de login e bloqueia após 5 tentativas"""
        if sucesso:
            self.tentativas_login = 0
            self.ultimo_acesso = timezone.now()
            self.bloqueado_ate = None
        else:
            self.tentativas_login += 1
            if self.tentativas_login >= 5:
                # Bloqueia por 30 minutos
                self.bloqueado_ate = timezone.now() + timezone.timedelta(minutes=30)

        self.save()


class Pedido(models.Model):
    """Modelo de Pedido de separação"""

    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('EM_SEPARACAO', 'Em Separação'),
        ('AGUARDANDO_COMPRA', 'Aguardando Compra'),
        ('FINALIZADO', 'Finalizado'),
        ('CANCELADO', 'Cancelado'),
    ]

    LOGISTICA_CHOICES = [
        ('RETIRADA', 'Retirada'),
        ('ENTREGA', 'Entrega'),
        ('TRANSPORTADORA', 'Transportadora'),
        ('MOTOBOY', 'Motoboy'),
    ]

    EMBALAGEM_CHOICES = [
        ('CAIXA_PEQUENA', 'Caixa Pequena'),
        ('CAIXA_MEDIA', 'Caixa Média'),
        ('CAIXA_GRANDE', 'Caixa Grande'),
        ('SACO_PLASTICO', 'Saco Plástico'),
        ('SEM_EMBALAGEM', 'Sem Embalagem'),
    ]

    numero_orcamento = models.CharField(max_length=50, unique=True, verbose_name='Número do Orçamento')
    codigo_cliente = models.CharField(max_length=100, verbose_name='Código do Cliente')
    nome_cliente = models.CharField(max_length=200, verbose_name='Nome do Cliente')
    vendedor = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='pedidos',
        verbose_name='Vendedor'
    )
    data = models.DateField(verbose_name='Data')
    logistica = models.CharField(
        max_length=100,
        blank=True,
        choices=LOGISTICA_CHOICES,
        verbose_name='Logística'
    )
    embalagem = models.CharField(
        max_length=100,
        blank=True,
        choices=EMBALAGEM_CHOICES,
        verbose_name='Embalagem'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDENTE',
        verbose_name='Status'
    )
    observacoes = models.TextField(blank=True, verbose_name='Observações')
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')
    data_finalizacao = models.DateTimeField(null=True, blank=True, verbose_name='Data de Finalização')

    # Soft delete
    deletado = models.BooleanField(default=False, verbose_name='Deletado')
    deletado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos_deletados',
        verbose_name='Deletado Por'
    )
    deletado_em = models.DateTimeField(null=True, blank=True, verbose_name='Deletado Em')

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-data_criacao']

    def __str__(self):
        return f"Pedido {self.numero_orcamento} - {self.nome_cliente}"

    def pode_ser_finalizado(self):
        """
        Verifica se o pedido pode ser finalizado.
        Regra: Todos os itens devem estar (separado=True OU substituido=True)
        E nenhum item pode estar em_compra=True
        """
        itens = self.itens.all()

        if not itens.exists():
            return False, 'Pedido não possui itens'

        # Verifica se algum item está em compra
        itens_em_compra = itens.filter(em_compra=True)
        if itens_em_compra.exists():
            return False, f'{itens_em_compra.count()} item(ns) ainda está(ão) em compra'

        # Verifica se todos os itens estão separados ou substituídos
        itens_pendentes = itens.filter(separado=False, substituido=False)
        if itens_pendentes.exists():
            return False, f'{itens_pendentes.count()} item(ns) não foi(ram) separado(s) ou substituído(s)'

        return True, 'OK'

    def get_card_status(self):
        """
        Retorna o status do card baseado no estado dos itens.
        Prioridade:
        1. AGUARDANDO_COMPRA - Se qualquer item está em compra (em_compra=True)
        2. CONCLUIDO - Se 100% dos itens estão (separado OU substituido OU compra_realizada)
        3. EM_SEPARACAO - Se qualquer item foi separado/substituído
        4. NAO_INICIADO - Nenhum progresso ainda

        Returns:
            tuple: (status_code, status_display)
        """
        itens = self.itens.all()

        if not itens.exists():
            return 'NAO_INICIADO', 'Não Iniciado'

        total_itens = itens.count()

        # Prioridade 1: Verifica se algum item está em compra
        if itens.filter(em_compra=True).exists():
            return 'AGUARDANDO_COMPRA', 'Aguardando Compra'

        # Conta itens concluídos: separado OU substituído OU compra_realizada
        from django.db.models import Q
        itens_concluidos = itens.filter(
            Q(separado=True) | Q(substituido=True) | Q(compra_realizada=True)
        ).count()

        # Prioridade 2: Verifica se está 100% concluído
        if itens_concluidos == total_itens:
            return 'CONCLUIDO', 'Concluído'

        # Prioridade 3: Verifica se há algum progresso
        if itens_concluidos > 0:
            return 'EM_SEPARACAO', 'Em Separação'

        # Prioridade 4: Nenhum progresso
        return 'NAO_INICIADO', 'Não Iniciado'


    def get_card_status_css(self):
        """
        Retorna o card_status formatado para uso em classes CSS.
        Converte NAO_INICIADO -> nao-iniciado, EM_SEPARACAO -> em-separacao, etc.
        """
        card_status_code, _ = self.get_card_status()
        return card_status_code.lower().replace('_', '-')


class Produto(models.Model):
    """Modelo de Produto"""

    codigo = models.CharField(max_length=50, unique=True, verbose_name='Código')
    descricao = models.CharField(max_length=500, verbose_name='Descrição')
    criado_automaticamente = models.BooleanField(default=False, verbose_name='Criado Automaticamente')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.descricao}"


class ItemPedido(models.Model):
    """Modelo de Item de Pedido"""

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Pedido'
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name='itens_pedido',
        verbose_name='Produto'
    )
    quantidade_solicitada = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Quantidade Solicitada'
    )
    preco_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Preço Unitário'
    )

    # Separação (tudo ou nada)
    separado = models.BooleanField(default=False, verbose_name='Separado')
    separado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itens_separados',
        verbose_name='Separado Por'
    )
    separado_em = models.DateTimeField(null=True, blank=True, verbose_name='Separado Em')

    # Compra
    em_compra = models.BooleanField(default=False, verbose_name='Em Compra')
    marcado_compra_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itens_marcados_compra',
        verbose_name='Marcado para Compra Por'
    )
    marcado_compra_em = models.DateTimeField(null=True, blank=True, verbose_name='Marcado para Compra Em')

    # Substituição
    substituido = models.BooleanField(default=False, verbose_name='Substituído')
    produto_substituto = models.CharField(max_length=200, blank=True, verbose_name='Produto Substituto')

    # Compra realizada
    compra_realizada = models.BooleanField(default=False, verbose_name='Compra Realizada')
    compra_realizada_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compras_realizadas',
        verbose_name='Compra Realizada Por'
    )
    compra_realizada_em = models.DateTimeField(null=True, blank=True, verbose_name='Compra Realizada Em')

    class Meta:
        verbose_name = 'Item de Pedido'
        verbose_name_plural = 'Itens de Pedido'
        ordering = ['id']

    def __str__(self):
        return f"{self.produto.codigo} - Qtd: {self.quantidade_solicitada}"

    @property
    def valor_total(self):
        """Calcula o valor total do item"""
        return self.quantidade_solicitada * self.preco_unitario


class LogAuditoria(models.Model):
    """Modelo de Log de Auditoria"""

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs',
        verbose_name='Usuário'
    )
    acao = models.CharField(max_length=50, verbose_name='Ação')
    modelo = models.CharField(max_length=50, verbose_name='Modelo')
    objeto_id = models.IntegerField(verbose_name='ID do Objeto')
    dados_anteriores = models.JSONField(null=True, blank=True, verbose_name='Dados Anteriores')
    dados_novos = models.JSONField(null=True, blank=True, verbose_name='Dados Novos')
    ip = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP')
    user_agent = models.CharField(max_length=255, blank=True, verbose_name='User Agent')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Timestamp')

    class Meta:
        verbose_name = 'Log de Auditoria'
        verbose_name_plural = 'Logs de Auditoria'
        ordering = ['-timestamp']

    def __str__(self):
        usuario_str = f"{self.usuario}" if self.usuario else "Sistema"
        return f"{usuario_str} - {self.acao} - {self.modelo} #{self.objeto_id}"
