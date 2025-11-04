# 📋 PLANO DE DESENVOLVIMENTO - Sistema de Separação de Pedidos PMCELL

## 🎯 VISÃO GERAL DO PROJETO
**Objetivo**: Sistema Django para gestão de separação de pedidos com processamento de PDF, WebSocket em tempo real e controle multi-usuário.

**Características principais**:
- Uso interno da PMCELL
- 30-40 pedidos/mês
- Até 10 usuários simultâneos
- Deploy no Railway (plano free)
- Sistema sempre disponível (24/7)
- Horário comercial considerado para métricas: 7:30-17h

## 📊 STATUS GERAL DO PROJETO
- **Início**: 04/11/2024
- **Status Atual**: EM DESENVOLVIMENTO
- **Fase Atual**: FASE 1 - ✅ COMPLETA | Próxima: FASE 2
- **Progresso Total**: 20%
- **GitHub**: https://github.com/nycolasmancini/pmcell-separacao
- **URL Produção**: https://web-production-312d.up.railway.app

## 🔧 STACK TÉCNICO DEFINIDO
- **Backend**: Django 4.2 + Django Channels (WebSocket)
- **Banco**: SQLite (desenvolvimento e produção inicial)
- **Cache/WebSocket**: Redis em memória (channels memory layer)
- **Frontend**: Django Templates + HTMX + Alpine.js + Tailwind CSS
- **PDF**: pdfplumber para extração
- **Deploy**: Railway (plano free)
- **Repositório**: GitHub (a ser criado)

## 📁 ESTRUTURA DO PROJETO
```
pmcell/
├── manage.py
├── requirements.txt
├── Procfile
├── runtime.txt
├── railway.json
├── .env.example
├── .gitignore
├── README.md
├── planejamento.md
├── pmcell_settings/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── consumers.py
│   │   ├── pdf_parser.py
│   │   ├── permissions.py
│   │   ├── admin.py
│   │   └── migrations/
│   └── api/
│       ├── __init__.py
│       ├── serializers.py
│       └── views.py
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── pedido_detalhe.html
│   ├── upload_pdf.html
│   ├── painel_compras.html
│   └── components/
├── static/
│   ├── css/
│   ├── js/
│   └── img/
└── tests/
```

## 🚀 FASES DE DESENVOLVIMENTO

### **FASE 0: Deploy Inicial no Railway** ✅ COMPLETA
**Objetivo**: Configurar deploy básico funcionando no Railway antes de desenvolver features

**Status**: ✅ COMPLETA - 04/11/2024

**Tarefas**:
- [x] Criar projeto Django mínimo
- [x] Configurar para Railway (Procfile, runtime.txt, requirements.txt)
- [x] Criar repositório no GitHub
- [x] Conectar GitHub ao Railway
- [x] Fazer primeiro deploy de teste
- [x] Verificar que está rodando em produção
- [x] Configurar variáveis de ambiente

**Entregas**:
- **GitHub**: https://github.com/nycolasmancini/pmcell-separacao
- **URL Produção**: https://web-production-312d.up.railway.app
- **Deploy Automático**: Configurado (push to main = deploy)

**Resultado**: ✅ Página inicial Django rodando com sucesso no Railway

---

### **FASE 1: Setup e Estrutura Base** ✅ COMPLETA
**Status**: ✅ COMPLETA - 04/11/2024

**Tarefas**:
- [x] Estrutura completa de diretórios (/apps/core, /apps/api)
- [x] Configurar settings.py (SQLite, timezone São Paulo, AUTH_USER_MODEL)
- [x] Criar app 'core' com estrutura completa
- [x] Configurar Django Channels (ASGI + InMemoryChannelLayer)
- [x] Criar modelos: Usuario, Pedido, ItemPedido, Produto, LogAuditoria
- [x] Fazer migrations iniciais + data migration para admin
- [x] Configurar admin Django completo com customizações
- [x] Setup Tailwind CSS via CDN (já estava na FASE 0)
- [x] Template base.html com HTMX (já estava na FASE 0)
- [x] Configurar arquivos estáticos com WhiteNoise (já estava na FASE 0)

**Modelos criados**:
- [x] Usuario (AbstractBaseUser + PermissionsMixin)
- [x] Pedido (com soft delete e validação)
- [x] ItemPedido (separação tudo-ou-nada)
- [x] Produto (criação automática via PDF)
- [x] LogAuditoria (auditoria completa)

**Entregas**:
- ✅ 5 modelos funcionais com migrations aplicadas
- ✅ Admin Django completo com badges e customizações
- ✅ Django Channels configurado (Daphne)
- ✅ Usuário admin inicial criado (1000/1234)
- ✅ Deploy no Railway atualizado

---

### **FASE 2: Sistema de Login e Permissões** (2 dias)
**Status**: ⏰ Pendente

**Tarefas**:
- [ ] Backend de autenticação customizada (numero_login + PIN)
- [ ] Hash seguro para PINs
- [ ] Tela de login responsiva
- [ ] Sistema de bloqueio após 5 tentativas
- [ ] Rate limiting
- [ ] Decorators de permissão (@vendedor_required, @separador_required, etc)
- [ ] View para admin resetar PINs
- [ ] Logout e gerenciamento de sessão
- [ ] Timeout de sessão (8 horas)
- [ ] Middleware de auditoria para todas ações

**Views criadas**:
- [ ] LoginView
- [ ] LogoutView
- [ ] ResetPinView (admin)

---

### **FASE 3: Upload e Processamento de PDF** (3 dias)
**Status**: ⏰ Pendente

**Tarefas**:
- [ ] Tela de upload de PDF
- [ ] Configurar pdfplumber
- [ ] Parser de PDF - extrair cabeçalho
- [ ] Parser de PDF - extrair produtos
- [ ] Validação de dados extraídos
- [ ] Criação automática de produtos (baseado em código)
- [ ] Detecção de duplicatas
- [ ] Criar Pedido e ItemPedido
- [ ] Tratamento de erros
- [ ] Feedback visual do processamento

**Views criadas**:
- [ ] UploadPDFView
- [ ] ProcessarPDFView

**Funções implementadas**:
- [ ] extrair_dados_pdf()
- [ ] validar_orcamento()
- [ ] criar_pedido_from_pdf()

---

### **FASE 4: Dashboard com WebSocket** (2 dias)
**Status**: ⏰ Pendente

**Tarefas**:
- [ ] Dashboard principal com cards
- [ ] Consumer WebSocket para dashboard
- [ ] Conexão automática WebSocket
- [ ] Reconexão em caso de queda
- [ ] Cards de pedidos com status
- [ ] Filtros: status, vendedor, data
- [ ] Indicadores: em separação, finalizados hoje
- [ ] Broadcast de novos pedidos
- [ ] Update em tempo real

**Views criadas**:
- [ ] DashboardView

**WebSocket**:
- [ ] DashboardConsumer
- [ ] Eventos: pedido_criado, pedido_atualizado, pedido_finalizado

---

### **FASE 5: Detalhes e Separação de Pedidos** (3 dias)
**Status**: ⏰ Pendente

**Tarefas**:
- [ ] Tela de detalhes do pedido
- [ ] Lista de itens do pedido
- [ ] Botão "Separar" por item
- [ ] Marcar quantidade separada
- [ ] Botão "Marcar para Compra"
- [ ] Modal de confirmação (marcar em outros pedidos?)
- [ ] Botão "Substituir" com modal
- [ ] Campo para informar produto substituto
- [ ] Botão "Finalizar Pedido"
- [ ] Validação: todos itens separados
- [ ] WebSocket updates dos itens
- [ ] Soft delete de pedidos (vendedor)

**Views criadas**:
- [ ] PedidoDetalheView
- [ ] SepararItemView
- [ ] MarcarCompraView
- [ ] SubstituirProdutoView
- [ ] FinalizarPedidoView
- [ ] DeletarPedidoView

---

### **FASE 6: Painel de Compras** (2 dias)
**Status**: ⏰ Pendente

**Tarefas**:
- [ ] Tela do painel de compras
- [ ] Listar itens com em_compra=True
- [ ] Agrupamento por produto
- [ ] Mostrar pedidos relacionados
- [ ] Botão "Confirmar Compra"
- [ ] Histórico de compras
- [ ] Filtros e busca
- [ ] WebSocket para atualizações

**Views criadas**:
- [ ] PainelComprasView
- [ ] ConfirmarCompraView
- [ ] HistoricoComprasView

---

### **FASE 7: Gestão de Usuários** (1 dia)
**Status**: ⏰ Pendente

**Tarefas**:
- [ ] CRUD de usuários (admin only)
- [ ] Formulário criar usuário
- [ ] Gerar número login automático (4 dígitos)
- [ ] Definir PIN inicial
- [ ] Editar usuário
- [ ] Ativar/desativar usuário
- [ ] Resetar PIN
- [ ] Lista de usuários com último acesso
- [ ] Validações e permissões

**Views criadas**:
- [ ] ListaUsuariosView
- [ ] CriarUsuarioView
- [ ] EditarUsuarioView
- [ ] ResetarPinView

---

### **FASE 8: Histórico e Métricas** (2 dias)
**Status**: ⏰ Pendente

**Tarefas**:
- [ ] Tela de histórico
- [ ] Filtros: período, vendedor, status
- [ ] Paginação de resultados
- [ ] Tela de métricas básicas
- [ ] Cálculo tempo médio (considera horário comercial)
- [ ] Taxa de conclusão
- [ ] Pedidos por período
- [ ] Botão atualizar métricas
- [ ] Indicador de cálculo em andamento

**Views criadas**:
- [ ] HistoricoView
- [ ] MetricasView

**Funções**:
- [ ] calcular_tempo_util()
- [ ] gerar_metricas()

---

### **FASE 9: Ajustes e Polimento** (2 dias)
**Status**: ⏰ Pendente

**Tarefas**:
- [ ] Revisão de todas as permissões
- [ ] Mensagens de feedback (sucesso/erro)
- [ ] Loading states
- [ ] Melhorias de UI/UX
- [ ] Validações frontend
- [ ] Otimização de queries
- [ ] Testes manuais completos
- [ ] Ajustes de responsividade
- [ ] Documentação de uso

---

### **FASE 10: Deploy Final e Testes** (1 dia)
**Status**: ⏰ Pendente

**Tarefas**:
- [ ] Revisar configurações de produção
- [ ] Testar todas funcionalidades em produção
- [ ] Configurar backup do SQLite
- [ ] Criar usuários iniciais
- [ ] Documentar processo de manutenção
- [ ] Treinar usuários
- [ ] Monitorar primeiros dias

---

## 📝 MODELOS DE DADOS DETALHADOS

### Usuario (CustomUser)
```python
- numero_login: IntegerField (único, 4 dígitos)
- nome: CharField(200)
- tipo: CharField (VENDEDOR|SEPARADOR|COMPRADORA|ADMINISTRADOR)
- pin_hash: CharField(128)
- ativo: BooleanField(default=True)
- ultimo_acesso: DateTimeField(null=True)
- tentativas_login: IntegerField(default=0)
- bloqueado_ate: DateTimeField(null=True)
- criado_em: DateTimeField(auto_now_add=True)
- atualizado_em: DateTimeField(auto_now=True)
```

### Pedido
```python
- numero_orcamento: CharField(50, unique=True)
- codigo_cliente: CharField(100)
- nome_cliente: CharField(200)
- vendedor: ForeignKey(Usuario)
- data: DateField
- logistica: CharField(choices=LOGISTICA_CHOICES)
- embalagem: CharField(choices=EMBALAGEM_CHOICES)
- status: CharField(choices=STATUS_CHOICES)
- observacoes: TextField(blank=True)
- data_criacao: DateTimeField(auto_now_add=True)
- data_finalizacao: DateTimeField(null=True)
- deletado: BooleanField(default=False)
- deletado_por: ForeignKey(Usuario, null=True)
- deletado_em: DateTimeField(null=True)
```

### ItemPedido
```python
- pedido: ForeignKey(Pedido, on_delete=CASCADE)
- produto: ForeignKey(Produto)
- quantidade_solicitada: DecimalField(max_digits=10, decimal_places=2)
- quantidade_separada: DecimalField(max_digits=10, decimal_places=2, default=0)
- preco_unitario: DecimalField(max_digits=10, decimal_places=2)
- separado: BooleanField(default=False)
- separado_por: ForeignKey(Usuario, null=True)
- separado_em: DateTimeField(null=True)
- em_compra: BooleanField(default=False)
- marcado_compra_por: ForeignKey(Usuario, null=True)
- marcado_compra_em: DateTimeField(null=True)
- substituido: BooleanField(default=False)
- produto_substituto: CharField(200, blank=True)
- compra_realizada: BooleanField(default=False)
- compra_realizada_por: ForeignKey(Usuario, null=True)
- compra_realizada_em: DateTimeField(null=True)
```

### Produto
```python
- codigo: CharField(50, unique=True)
- descricao: CharField(500)
- criado_automaticamente: BooleanField(default=False)
- criado_em: DateTimeField(auto_now_add=True)
- atualizado_em: DateTimeField(auto_now=True)
```

### LogAuditoria
```python
- usuario: ForeignKey(Usuario, null=True)
- acao: CharField(50)
- modelo: CharField(50)
- objeto_id: IntegerField()
- dados_anteriores: JSONField(null=True)
- dados_novos: JSONField(null=True)
- ip: GenericIPAddressField(null=True)
- user_agent: CharField(255, blank=True)
- timestamp: DateTimeField(auto_now_add=True)
```

## 🔐 DECISÕES TÉCNICAS TOMADAS

1. **PIN de 4 dígitos**: Mantido conforme solicitado (uso interno)
2. **SQLite + Redis local**: Para economizar recursos no Railway free
3. **Soft delete sempre**: Para manter histórico completo
4. **Sistema sempre disponível**: Horário comercial apenas para cálculos
5. **WebSocket essencial**: Todas atualizações em tempo real
6. **Produtos automáticos**: Criados baseados no código do PDF
7. **Marcar compra**: Pergunta se quer marcar em outros pedidos

## 📈 MÉTRICAS DE PROGRESSO

- **Fases Completas**: 2/10 (FASE 0 ✅, FASE 1 ✅)
- **Views Implementadas**: 1/25 (home_view)
- **Modelos Criados**: 5/5 (Usuario, Pedido, ItemPedido, Produto, LogAuditoria ✅)
- **Testes Escritos**: 0
- **Deploy Railway**: ✅ FUNCIONANDO - https://web-production-312d.up.railway.app

## 🐛 BUGS E PROBLEMAS CONHECIDOS

*Nenhum bug registrado ainda*

## 📚 APRENDIZADOS E NOTAS

*Seção para documentar aprendizados durante o desenvolvimento*

## 🔄 ÚLTIMAS ATUALIZAÇÕES

### 04/11/2024 - Criação do Planejamento
- Documento de planejamento criado
- Estrutura do projeto definida
- Fases de desenvolvimento organizadas
- Prioridade: Deploy no Railway primeiro

### 04/11/2024 - FASE 0 Completa (19:30)
- ✅ Projeto Django criado e configurado
- ✅ Configurações para Railway (Procfile, runtime.txt, requirements.txt)
- ✅ Página inicial funcionando localmente
- ✅ Repositório GitHub criado: https://github.com/nycolasmancini/pmcell-separacao
- ✅ Código enviado para GitHub
- ✅ Deploy no Railway confirmado funcionando
- ✅ URL de produção: https://web-production-312d.up.railway.app

**Estrutura criada**:
- Sistema de templates com base.html e home.html
- Configuração para múltiplos ambientes (dev/prod)
- WhiteNoise configurado para arquivos estáticos
- Settings preparado para Railway
- Deploy automático configurado (push to main = deploy)

**Conquistas da FASE 0**:
1. Ambiente de desenvolvimento configurado
2. Deploy contínuo funcionando
3. Base sólida para as próximas fases
4. Estrutura de projeto organizada

### 04/11/2024 - FASE 1 Completa (21:30)
- ✅ Estrutura /apps/core e /apps/api criada
- ✅ 5 modelos implementados com sucesso
- ✅ Usuario: AbstractBaseUser customizado com autenticação por numero_login + PIN
- ✅ Pedido, ItemPedido, Produto, LogAuditoria: Modelos de negócio completos
- ✅ Django Channels configurado (ASGI + Daphne + InMemoryChannelLayer)
- ✅ Admin Django completo com customizações e badges coloridos
- ✅ Migrations aplicadas + Data migration criando admin inicial (1000/1234)
- ✅ Procfile atualizado para Daphne (suporte WebSocket)
- ✅ Dependências instaladas: channels, daphne, pdfplumber
- ✅ Deploy no Railway atualizado com sucesso

**Estrutura implementada**:
- Usuario com manager customizado e métodos set_pin(), check_pin(), pode_fazer_login()
- Pedido com soft delete e método pode_ser_finalizado()
- ItemPedido com separação tudo-ou-nada (Boolean)
- Produto com flag de criação automática
- LogAuditoria com JSONField para rastreamento completo
- Admin com inline de ItemPedido, badges de status, filtros avançados

**Decisões técnicas tomadas**:
1. AbstractBaseUser (sistema completamente customizado)
2. numero_login informado manualmente pelo admin (4 dígitos)
3. PIN definido pelo admin na criação (4 dígitos)
4. Status pedido: PENDENTE, EM_SEPARACAO, AGUARDANDO_COMPRA, FINALIZADO, CANCELADO
5. Separação tudo-ou-nada (não permite parcial)
6. Finalização valida: 100% separados+substituídos E nenhum em_compra
7. InMemoryChannelLayer (ideal para Railway free tier)

**Conquistas da FASE 1**:
1. Base de dados completa e funcional
2. Sistema de autenticação customizado pronto
3. WebSocket configurado para tempo real
4. Admin funcional para gestão
5. Usuário admin criado automaticamente

---

**Próxima ação**: Iniciar FASE 2 - Sistema de Login e Permissões