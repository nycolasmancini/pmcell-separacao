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
- **Fase Atual**: FASE 8 - ✅ COMPLETA | Próxima: FASE 9
- **Progresso Total**: 85%
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

### **FASE 2: Sistema de Login e Permissões** ✅ COMPLETA
**Status**: ✅ COMPLETA - 04/11/2024

**Tarefas**:
- [x] Backend de autenticação customizada (numero_login + PIN)
- [x] Hash seguro para PINs
- [x] Tela de login responsiva
- [x] Sistema de bloqueio após 5 tentativas (30 minutos)
- [x] Rate limiting (10 tentativas/15min por numero_login)
- [x] Decorators de permissão (@vendedor_required, @separador_required, etc)
- [x] View para admin resetar PINs
- [x] Logout e gerenciamento de sessão
- [x] Timeout de sessão (8 horas)
- [x] Middleware de auditoria para todas ações

**Views criadas**:
- [x] LoginView (com validações completas)
- [x] LogoutView (com auditoria)
- [x] ResetPinView (admin only)
- [x] Dashboard básico (será expandido na FASE 4)

**Templates criados**:
- [x] login.html (responsivo, validação frontend)
- [x] dashboard.html (placeholder para FASE 4)
- [x] reset_pin.html (interface admin)
- [x] base.html atualizado (navbar com menu dropdown)

**Entregas**:
- ✅ Sistema de login funcional com bloqueio e rate limiting
- ✅ Desbloqueio automático (30min) + manual (admin)
- ✅ Middleware de auditoria registrando todas ações
- ✅ Decorators de permissão funcionais
- ✅ Testes completos passando (login + bloqueio)
- ✅ Deploy no Railway atualizado

---

### **FASE 3: Upload e Processamento de PDF** ✅ COMPLETA
**Status**: ✅ COMPLETA - 04/11/2024

**Tarefas**:
- [x] Tela de upload de PDF com drag-and-drop
- [x] Configurar pdfplumber
- [x] Parser de PDF - extrair cabeçalho (número orçamento, cliente, data)
- [x] Parser de PDF - extrair produtos (código, descrição, quantidade, preço)
- [x] Validação de dados extraídos
- [x] Criação automática de produtos (baseado em código)
- [x] Detecção de duplicatas (rejeita upload se orçamento já existe)
- [x] Criar Pedido e ItemPedido via transaction
- [x] Tratamento de erros completo
- [x] Feedback visual do processamento (loading states)
- [x] Formulário de confirmação (logística + embalagem)

**Arquivos criados**:
- [x] apps/core/pdf_parser.py (módulo de extração)
- [x] apps/core/forms.py (UploadPDFForm, ConfirmarPedidoForm)
- [x] templates/upload_pdf.html (interface com drag-and-drop)
- [x] templates/confirmar_pedido.html (preview + formulário)

**Views implementadas**:
- [x] upload_pdf_view (upload + processamento inicial)
- [x] confirmar_pedido_view (confirmação + criação do pedido)
- [x] pedido_detalhe_view (stub temporário, FASE 5)

**Funções implementadas**:
- [x] extrair_dados_pdf() - extração completa do PDF
- [x] extrair_cabecalho() - cabeçalho do orçamento
- [x] extrair_produtos() - tabela de produtos
- [x] processar_linha_produto() - parsing individual
- [x] limpar_numero() - normalização de valores
- [x] validar_orcamento() - validações de negócio

**Entregas**:
- ✅ Sistema completo de upload e processamento de PDF funcionando
- ✅ Parser robusto testado com 7 PDFs reais diferentes
- ✅ Validação de duplicatas implementada
- ✅ Produtos criados automaticamente com flag `criado_automaticamente=True`
- ✅ Interface responsiva com feedback visual
- ✅ Dashboard atualizado com link "Novo Orçamento"
- ✅ Navbar atualizada com acesso rápido
- ✅ Auditoria completa de todas ações

---

### **FASE 4: Dashboard com WebSocket** ✅ COMPLETA
**Status**: ✅ COMPLETA - 04/11/2024

**Tarefas**:
- [x] Dashboard principal com cards
- [x] Consumer WebSocket para dashboard
- [x] Conexão automática WebSocket
- [x] Reconexão em caso de queda
- [x] Cards de pedidos com status
- [x] Filtros: status, vendedor (client-side com Alpine.js)
- [x] Indicadores: tempo médio separação hoje, pedidos em aberto, total hoje
- [x] Broadcast de novos pedidos
- [x] Update em tempo real

**Views criadas**:
- [x] DashboardView (função dashboard() atualizada)

**WebSocket**:
- [x] DashboardConsumer
- [x] Eventos: pedido_criado, pedido_atualizado, pedido_finalizado

**Arquivos criados**:
- [x] apps/core/utils.py (cálculo de tempo útil)
- [x] apps/core/routing.py (rotas WebSocket)
- [x] static/js/dashboard.js (lógica WebSocket)

**Arquivos atualizados**:
- [x] apps/core/consumers.py (DashboardConsumer implementado)
- [x] apps/core/views.py (dashboard() e confirmar_pedido_view() com broadcast)
- [x] pmcell_settings/asgi.py (routing habilitado)
- [x] templates/dashboard.html (indicadores + filtros + lista de pedidos)

**Entregas**:
- ✅ Dashboard mostra pedidos ativos com métricas do dia
- ✅ WebSocket conecta automaticamente e reconecta em caso de queda
- ✅ Broadcast silencioso quando novo pedido é criado
- ✅ Filtros client-side (status, vendedor) funcionando com Alpine.js
- ✅ Indicadores: tempo médio (horário comercial), pedidos em aberto, total hoje
- ✅ Interface moderna e responsiva
- ✅ Status de conexão WebSocket (indicador visual)

---

### **FASE 5: Detalhes e Separação de Pedidos** ✅ COMPLETA
**Status**: ✅ COMPLETA - 05/11/2024

**Tarefas**:
- [x] Tela de detalhes do pedido
- [x] Lista de itens do pedido
- [x] Botão "Separar" por item (tudo-ou-nada)
- [x] Botão "Marcar para Compra"
- [x] Modal de confirmação (marcar em outros pedidos)
- [x] Botão "Substituir" com modal
- [x] Campo para informar produto substituto (texto livre)
- [x] Botão "Finalizar Pedido"
- [x] Validação: todos itens separados/substituídos e nenhum em compra
- [x] WebSocket updates dos itens em tempo real
- [x] Soft delete de pedidos (vendedor criador ou admin)

**Views criadas**:
- [x] pedido_detalhe_view (GET - mostra detalhes e itens)
- [x] separar_item_view (POST - SEPARADOR/ADMIN)
- [x] marcar_compra_view (GET/POST - COMPRADORA/ADMIN)
- [x] substituir_item_view (POST - SEPARADOR/ADMIN)
- [x] finalizar_pedido_view (POST - SEPARADOR/ADMIN)
- [x] deletar_pedido_view (POST - VENDEDOR criador/ADMIN)

**Forms criados**:
- [x] SubstituirProdutoForm (campo texto para produto substituto)
- [x] MarcarCompraForm (checkbox múltiplo para outros pedidos)

**Templates criados**:
- [x] pedido_detalhe.html (com modais integrados em Alpine.js)

**JavaScript criado**:
- [x] static/js/pedido_detalhe.js (WebSocket client + Alpine.js app)

**WebSocket**:
- [x] PedidoDetalheConsumer (eventos: item_separado, item_em_compra, item_substituido, pedido_atualizado, pedido_finalizado, pedido_deletado)
- [x] Rota: ws/pedido/<int:pedido_id>/

**Entregas**:
- ✅ Sistema completo de separação de pedidos funcionando
- ✅ WebSocket com atualizações em tempo real de itens
- ✅ Modais para substituição e marcação de compra
- ✅ Validações de permissão (SEPARADOR, COMPRADORA, VENDEDOR)
- ✅ Marcar compra com opção de marcar em múltiplos pedidos
- ✅ Soft delete com permissões (vendedor criador ou admin)
- ✅ Interface moderna e responsiva com Alpine.js
- ✅ Auditoria completa de todas ações
- ✅ Broadcast para dashboard quando pedido é atualizado

---

### **FASE 6: Painel de Compras** ✅ COMPLETA
**Status**: ✅ COMPLETA - 05/11/2024

**Tarefas**:
- [x] Tela do painel de compras
- [x] Listar itens com em_compra=True
- [x] Agrupamento por produto
- [x] Mostrar pedidos relacionados
- [x] Botão "Confirmar Compra"
- [x] Histórico de compras (90 dias)
- [x] Filtros e busca (produto e pedido)
- [x] WebSocket para atualizações

**Views criadas**:
- [x] painel_compras_view (GET)
- [x] confirmar_compra_view (POST)
- [x] historico_compras_view (GET)

**WebSocket**:
- [x] PainelComprasConsumer (eventos: item_marcado_compra, compra_confirmada, item_separado_direto)
- [x] Rota: ws/painel-compras/

**Templates criados**:
- [x] painel_compras.html (com Alpine.js e filtros)
- [x] historico_compras.html (com paginação)

**JavaScript criado**:
- [x] static/js/painel_compras.js (WebSocket client + Alpine.js app)

**Entregas**:
- ✅ Sistema completo de painel de compras funcionando
- ✅ Agrupamento por produto com quantidade total
- ✅ Lista de pedidos relacionados expandível
- ✅ Confirmação de compra (marca compra_realizada=True)
- ✅ SEPARADOR pode separar itens marcados para compra (remove da lista)
- ✅ Histórico de compras dos últimos 90 dias com paginação
- ✅ Filtros por produto (código/descrição) e pedido específico
- ✅ WebSocket com atualizações em tempo real
- ✅ Card no dashboard mostrando itens aguardando compra
- ✅ Link no navbar para COMPRADORA e ADMINISTRADOR
- ✅ Auditoria completa de todas ações
- ✅ Interface moderna e responsiva com Tailwind CSS

---

### **FASE 7: Gestão de Usuários** ✅ COMPLETA
**Status**: ✅ COMPLETA - 05/11/2024

**Tarefas**:
- [x] CRUD de usuários (admin only)
- [x] Formulário criar usuário (admin insere numero_login e PIN manualmente)
- [x] Editar usuário (nome, tipo, ativo)
- [x] Ativar/desativar usuário (toggle)
- [x] Resetar PIN (apenas admin)
- [x] Lista de usuários com último acesso
- [x] Validações e permissões
- [x] Testes completos (15 testes passando)

**Forms criados**:
- [x] CriarUsuarioForm (numero_login, nome, tipo, PIN + confirmação)
- [x] EditarUsuarioForm (nome, tipo, ativo)
- [x] ResetarPinForm (novo PIN + confirmação)

**Views criadas**:
- [x] lista_usuarios_view (lista todos usuários)
- [x] criar_usuario_view (criar novo usuário)
- [x] editar_usuario_view (editar usuário existente)
- [x] resetar_pin_usuario_view (resetar PIN de usuário)
- [x] toggle_ativo_usuario_view (ativar/desativar via POST)

**Templates criados**:
- [x] lista_usuarios.html (tabela com todos usuários)
- [x] criar_usuario.html (formulário de criação)
- [x] editar_usuario.html (formulário de edição)
- [x] resetar_pin_usuario.html (formulário de reset)

**Decisões de implementação**:
- Admin insere numero_login manualmente (validação de duplicata)
- Admin define PIN inicial do usuário
- Apenas admin pode resetar PINs (usuários não podem alterar)
- Desativar usuário: bloqueia login + oculta das listas de filtros
- Dashboard já filtra apenas usuários ativos
- Login já valida se usuário está ativo
- Não pode desativar admin principal (1000)
- Resetar PIN também limpa tentativas e rate limit

**Entregas**:
- ✅ Sistema completo de CRUD de usuários funcionando
- ✅ Todas permissões implementadas (@administrador_required)
- ✅ Validações frontend e backend
- ✅ Navbar atualizado com link "Gerenciar Usuários" (admin only)
- ✅ Auditoria completa de todas ações
- ✅ Testes completos: 15 testes passando (test_user_management.py)
- ✅ Interface moderna e responsiva com Tailwind CSS

---

### **FASE 8: Histórico e Métricas** ✅ COMPLETA
**Status**: ✅ COMPLETA - 05/11/2024

**Tarefas**:
- [x] Tela de histórico
- [x] Filtros: período, vendedor, status
- [x] Paginação de resultados (20 por página)
- [x] Tela de métricas básicas
- [x] Cálculo tempo médio (considera horário comercial)
- [x] Taxa de conclusão
- [x] Pedidos por período
- [x] Botão atualizar métricas
- [x] Itens em compra (% e quantidade)

**Views criadas**:
- [x] historico_view (GET - filtros + paginação)
- [x] metricas_view (GET/POST - atualização manual)

**Forms criados**:
- [x] HistoricoFiltrosForm (data_inicio, data_fim, vendedor, status)

**Funções**:
- [x] calcular_metricas_periodo() (reutiliza calcular_tempo_util existente)

**Templates criados**:
- [x] historico.html (filtros + tabela + paginação)
- [x] metricas.html (cards + seletor de período + botão atualizar)

**Decisões de implementação**:
1. Histórico: apenas pedidos ativos (deletado=False)
2. Filtro vendedor: dropdown com todos vendedores ativos + opção "Todos"
3. Paginação: 20 pedidos por página
4. Métricas essenciais: tempo médio + itens para compra (% e quantidade)
5. Atualização: botão manual (sem WebSocket para economizar recursos)
6. Período padrão: últimos 30 dias (customizável: 7, 30, 90 dias ou período custom)
7. Navbar atualizado: links "Histórico" e "Métricas" acessíveis por todos usuários

**Entregas**:
- ✅ Sistema completo de histórico com filtros avançados
- ✅ Tela de métricas com indicadores principais
- ✅ Função calcular_metricas_periodo() completa
- ✅ Navbar atualizado com novos links
- ✅ Testes completos: 16 testes passando (test_historico_metricas.py)
- ✅ Interface moderna e responsiva com Tailwind CSS
- ✅ Auditoria completa de todas ações

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

- **Fases Completas**: 9/10 (FASE 0-8 ✅)
- **Views Implementadas**: 24/30+ (separação + compras + usuários + histórico/métricas ✅)
- **Modelos Criados**: 5/5 (Usuario, Pedido, ItemPedido, Produto, LogAuditoria ✅)
- **Templates Criados**: 15 (base, login, dashboard, reset_pin, upload_pdf, confirmar_pedido, pedido_detalhe, painel_compras, historico_compras, lista_usuarios, criar_usuario, editar_usuario, resetar_pin_usuario, historico, metricas ✅)
- **Forms Criados**: 8/9+ (UploadPDFForm, ConfirmarPedidoForm, SubstituirProdutoForm, MarcarCompraForm, CriarUsuarioForm, EditarUsuarioForm, ResetarPinForm, HistoricoFiltrosForm ✅)
- **Testes Escritos**: 4 (test_login.py ✅, test_bloqueio.py ✅, test_user_management.py ✅ - 15 testes, test_historico_metricas.py ✅ - 16 testes)
- **WebSocket**: 3 Consumers ✅ (DashboardConsumer, PedidoDetalheConsumer, PainelComprasConsumer)
- **JavaScript**: 3 arquivos ✅ (dashboard.js, pedido_detalhe.js, painel_compras.js)
- **Utils**: apps/core/utils.py ✅ (calcular_tempo_util, calcular_metricas_dia, calcular_metricas_periodo, formatar_tempo)
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

### 04/11/2024 - FASE 2 Completa (21:00)
- ✅ Sistema de autenticação funcional (numero_login + PIN)
- ✅ LoginView implementada com todas validações
- ✅ Bloqueio após 5 tentativas incorretas (30 minutos)
- ✅ Desbloqueio automático após 30 minutos
- ✅ Rate limiting: 10 tentativas por numero_login em 15 minutos
- ✅ LogoutView com auditoria
- ✅ ResetPinView para admin resetar PINs
- ✅ Middleware de auditoria (registra todas ações)
- ✅ Decorators de permissão completos
- ✅ Timeout de sessão: 8 horas
- ✅ Templates responsivos criados (login, dashboard, reset_pin)
- ✅ Navbar com menu dropdown e logout
- ✅ Testes completos: test_login.py e test_bloqueio.py
- ✅ Deploy no Railway atualizado

**Estrutura implementada**:
- Middleware: AuditoriaMiddleware (registra IP, user_agent, ação)
- Decorators: @login_required_custom, @vendedor_required, @separador_required, @compradora_required, @administrador_required, @admin_or_vendedor
- Views: login_view, logout_view, reset_pin_view, dashboard
- Templates: login.html, dashboard.html, reset_pin.html, base.html (atualizado)
- Rate limiting em memória (RATE_LIMIT_CACHE)
- Sistema de mensagens (success, error, warning, info)

**Testes realizados**:
1. ✅ Login com usuário 1000/1234 (sucesso)
2. ✅ Login com PIN incorreto (rejeitado)
3. ✅ Bloqueio após 5 tentativas
4. ✅ Desbloqueio automático (30 minutos)
5. ✅ Auditoria de login/logout
6. ✅ Dashboard acessível após login
7. ✅ Logout funcionando

**Conquistas da FASE 2**:
1. Sistema de login robusto e seguro
2. Auditoria completa de todas ações
3. Controle de permissões por tipo de usuário
4. Interface responsiva e moderna
5. Testes automatizados validando funcionalidades

---

### 04/11/2024 - FASE 3 Completa (23:00)
- ✅ Sistema completo de upload e processamento de PDF
- ✅ Módulo pdf_parser.py com extração robusta de dados
- ✅ Parser testado com 7 PDFs reais (100% de sucesso)
- ✅ Views: upload_pdf_view, confirmar_pedido_view
- ✅ Forms: UploadPDFForm, ConfirmarPedidoForm (logística + embalagem)
- ✅ Templates modernos: upload_pdf.html (drag-and-drop), confirmar_pedido.html (preview)
- ✅ Validação de duplicatas (rejeita orçamentos repetidos)
- ✅ Criação automática de produtos com flag criado_automaticamente=True
- ✅ Transaction atômica para criar Pedido + ItemPedido
- ✅ Dashboard atualizado com card "Novo Orçamento"
- ✅ Navbar atualizada com link direto
- ✅ Auditoria completa de upload e criação

**Estrutura criada**:
- Parser de PDF com regex robusto para cabeçalho e produtos
- Suporte a tabelas com 1 coluna (parsing via regex)
- Normalização de números (vírgulas, pontos, R$)
- Validação completa de dados extraídos
- Workflow: Upload → Preview → Confirmar → Pedido criado

**Conquistas da FASE 3**:
1. Sistema de upload 100% funcional e testado
2. Parser robusto que lida com diferentes formatos
3. Interface moderna com drag-and-drop
4. Validações de negócio implementadas
5. Fluxo completo de ponta a ponta

---

### 04/11/2024 - FASE 4 Completa (21:30)
- ✅ Dashboard principal implementado com lista de pedidos ativos
- ✅ WebSocket Consumer (DashboardConsumer) implementado completo
- ✅ Conexão WebSocket automática com reconexão exponencial (1s→30s)
- ✅ Broadcast em tempo real quando pedido é criado (silencioso)
- ✅ Filtros client-side com Alpine.js (status, vendedor)
- ✅ Indicadores no topo: tempo médio separação hoje, pedidos em aberto, total hoje
- ✅ Cálculo de tempo útil considerando horário comercial (7:30-17h, seg-sex)
- ✅ Status de conexão WebSocket (indicador visual verde/vermelho)
- ✅ Interface moderna e responsiva

**Arquivos criados**:
- apps/core/utils.py: funções calcular_tempo_util(), calcular_metricas_dia(), formatar_tempo()
- apps/core/routing.py: roteamento WebSocket
- static/js/dashboard.js: classe DashboardWebSocket com handlers de eventos

**Arquivos atualizados**:
- apps/core/consumers.py: DashboardConsumer implementado
- apps/core/views.py: dashboard() com queries + confirmar_pedido_view() com broadcast
- pmcell_settings/asgi.py: routing WebSocket habilitado
- templates/dashboard.html: reformulado completamente

**Funcionalidades implementadas**:
1. Dashboard mostra apenas pedidos ativos (PENDENTE, EM_SEPARACAO, AGUARDANDO_COMPRA)
2. Métricas calculadas em tempo real no servidor
3. WebSocket conecta automaticamente e exibe indicador de status
4. Broadcast silencioso quando novo pedido é criado (atualiza todos dashboards conectados)
5. Filtros client-side sem requisições ao servidor
6. Reconexão automática com exponential backoff (máx 10 tentativas)
7. Ping/pong para manter conexão ativa (30s)

**Conquistas da FASE 4**:
1. Sistema de tempo real 100% funcional
2. Dashboard completo e responsivo
3. Cálculo de métricas considerando horário comercial
4. Arquitetura WebSocket robusta com reconexão
5. Interface moderna e intuitiva

---

### 05/11/2024 - FASE 5 Completa (00:45)
- ✅ Sistema completo de separação de pedidos implementado
- ✅ PedidoDetalheConsumer WebSocket para atualizações em tempo real
- ✅ 6 views implementadas (pedido_detalhe, separar_item, marcar_compra, substituir_item, finalizar_pedido, deletar_pedido)
- ✅ 2 forms criados (SubstituirProdutoForm, MarcarCompraForm)
- ✅ Template pedido_detalhe.html com modais integrados (Alpine.js)
- ✅ JavaScript pedido_detalhe.js com WebSocket client e Alpine.js app
- ✅ URLs adicionadas para todas as ações de separação
- ✅ Broadcast WebSocket para dashboard quando pedido é atualizado

**Arquivos criados**:
- templates/pedido_detalhe.html: Tela de detalhes completa com lista de itens e modais
- static/js/pedido_detalhe.js: WebSocket client + Alpine.js app para interações
- apps/core/forms.py: SubstituirProdutoForm, MarcarCompraForm

**Arquivos atualizados**:
- apps/core/consumers.py: PedidoDetalheConsumer adicionado
- apps/core/routing.py: Rota ws/pedido/<int:pedido_id>/ adicionada
- apps/core/views.py: 6 views implementadas + pedido_detalhe_view completa
- pmcell_settings/urls.py: 5 URLs adicionadas para ações de separação
- apps/core/permissions.py: Imports de decorators adicionados

**Funcionalidades implementadas**:
1. Tela de detalhes mostra: info do pedido, estatísticas, lista de itens, progresso
2. Separar item (tudo-ou-nada): SEPARADOR/ADMIN
3. Marcar para compra: COMPRADORA/ADMIN + modal com outros pedidos
4. Substituir produto: SEPARADOR/ADMIN + campo texto livre
5. Finalizar pedido: SEPARADOR/ADMIN + validações completas
6. Deletar pedido (soft delete): VENDEDOR criador/ADMIN
7. WebSocket atualiza itens em tempo real (6 eventos diferentes)
8. Broadcast para dashboard quando pedido é atualizado
9. Modais com Alpine.js (substituir e marcar compra)
10. Auditoria completa de todas ações

**Decisões de implementação**:
1. Separação: tudo-ou-nada (não permite parcial)
2. Marcar compra: pergunta se quer marcar em outros pedidos (via modal)
3. Substituição: campo texto livre para informar produto substituto
4. Delete: vendedor criador ou admin a qualquer momento
5. Modais integrados no template (não como componentes separados)
6. Alpine.js para gerenciar estado e interações client-side
7. WebSocket com reconexão automática e ping/pong

**Conquistas da FASE 5**:
1. Sistema de separação completo e funcional
2. WebSocket em tempo real para cada pedido
3. Interface moderna com Alpine.js e Tailwind CSS
4. Permissões corretamente implementadas por tipo de usuário
5. Validações de negócio robustas
6. Auditoria completa com IP e user agent
7. Broadcast para múltiplos groups (pedido específico + dashboard)

---

### 05/11/2024 - FASE 6 Completa (22:00)
- ✅ Sistema completo de painel de compras implementado
- ✅ PainelComprasConsumer WebSocket para atualizações em tempo real
- ✅ 3 views implementadas (painel_compras, confirmar_compra, historico_compras)
- ✅ 2 templates criados (painel_compras.html, historico_compras.html)
- ✅ JavaScript painel_compras.js com WebSocket client e Alpine.js app
- ✅ URLs adicionadas para todas as rotas de compras
- ✅ Navbar atualizada com link para painel de compras
- ✅ Dashboard atualizado com card mostrando itens aguardando compra

**Arquivos criados**:
- templates/painel_compras.html: Tela principal com lista agrupada por produto
- templates/historico_compras.html: Histórico dos últimos 90 dias com paginação
- static/js/painel_compras.js: WebSocket client + Alpine.js app
- apps/core/consumers.py: PainelComprasConsumer adicionado

**Arquivos atualizados**:
- apps/core/views.py: 3 views adicionadas + separar_item_view atualizada
- apps/core/routing.py: Rota ws/painel-compras/ adicionada
- pmcell_settings/urls.py: 3 URLs adicionadas (painel-compras, confirmar, historico)
- templates/base.html: Link "Painel de Compras" adicionado ao navbar
- templates/dashboard.html: Card de itens aguardando compra adicionado

**Funcionalidades implementadas**:
1. Painel mostra itens agrupados por produto com quantidade total
2. Lista expandível de pedidos relacionados para cada produto
3. Confirmar compra: marca compra_realizada=True para todos itens do produto
4. SEPARADOR pode separar itens marcados para compra (remove da lista)
5. Histórico de compras dos últimos 90 dias com paginação (20 por página)
6. Filtros por produto (código/descrição) e por número de pedido
7. WebSocket com atualizações em tempo real (3 eventos diferentes)
8. Card no dashboard mostrando contagem de itens aguardando compra
9. Auditoria completa de todas ações
10. Interface responsiva com Tailwind CSS e Alpine.js

**Decisões de implementação**:
1. Compra confirmada: cria novo status compra_realizada=True (não remove de em_compra)
2. SEPARADOR pode separar itens que estão em compra (achado no estoque)
3. Histórico: 90 dias de dados com paginação de 20 itens por página
4. Agrupamento: por produto com quantidade total e lista de pedidos
5. Filtros: client-side com Alpine.js (sem reload da página)
6. WebSocket: reconexão automática e broadcast para painel e dashboard
7. Card no dashboard: visível apenas para COMPRADORA e ADMINISTRADOR

**Conquistas da FASE 6**:
1. Sistema de compras completo e funcional
2. WebSocket em tempo real para painel de compras
3. Interface moderna com filtros e agrupamento
4. Histórico com paginação eficiente
5. Integração com dashboard e navbar
6. Auditoria completa de todas ações
7. Workflow completo: marcar → confirmar → separar

---

### 05/11/2024 - FASE 7 Completa (23:30)
- ✅ Sistema completo de gestão de usuários implementado
- ✅ 3 forms criados (CriarUsuarioForm, EditarUsuarioForm, ResetarPinForm)
- ✅ 5 views implementadas (lista, criar, editar, resetar_pin, toggle_ativo)
- ✅ 4 templates criados (lista_usuarios, criar_usuario, editar_usuario, resetar_pin_usuario)
- ✅ URLs adicionadas para todas as rotas de usuários
- ✅ Navbar atualizado com link "Gerenciar Usuários" (admin only)
- ✅ Testes completos: 15 testes passando (test_user_management.py)

**Arquivos criados**:
- templates/lista_usuarios.html: Lista de todos usuários com status e ações
- templates/criar_usuario.html: Formulário de criação com validações
- templates/editar_usuario.html: Formulário de edição (nome, tipo, ativo)
- templates/resetar_pin_usuario.html: Formulário de reset de PIN
- tests/test_user_management.py: 15 testes completos (forms + views)

**Arquivos atualizados**:
- apps/core/forms.py: 3 forms adicionados (CriarUsuarioForm, EditarUsuarioForm, ResetarPinForm)
- apps/core/views.py: 5 views adicionadas (lista, criar, editar, resetar_pin, toggle_ativo)
- pmcell_settings/urls.py: 5 URLs adicionadas para gestão de usuários
- templates/base.html: Link "Gerenciar Usuários" adicionado ao navbar (admin only)

**Funcionalidades implementadas**:
1. Lista de usuários mostrando: numero_login, nome, tipo, status, último acesso, ações
2. Criar usuário: admin insere numero_login e PIN manualmente (com validação de duplicata)
3. Editar usuário: nome, tipo, ativo (não permite editar numero_login)
4. Resetar PIN: admin define novo PIN (limpa tentativas e bloqueio)
5. Toggle ativar/desativar: POST request (não permite desativar admin 1000)
6. Validações: numero_login único, PIN numérico 4 dígitos, PIN confirmação
7. Usuários inativos: bloqueados no login + ocultos das listas de filtros
8. Auditoria completa de todas ações de gestão
9. Testes completos validando todas funcionalidades

**Decisões de implementação**:
1. Admin insere numero_login manualmente (não automático)
2. Admin define PIN inicial (não gerado automaticamente)
3. Apenas admin pode resetar PINs (usuários não podem alterar)
4. Desativar usuário: bloqueia login + oculta das listas
5. Dashboard já filtra apenas usuários ativos (ativo=True)
6. Login já valida se usuário está ativo antes de permitir acesso
7. Não permite desativar ou editar admin principal (numero_login=1000)
8. Resetar PIN também limpa tentativas_login, bloqueado_ate e rate limit

**Conquistas da FASE 7**:
1. Sistema completo de CRUD de usuários funcionando
2. Todas permissões implementadas (@administrador_required)
3. Validações robustas frontend e backend
4. Interface moderna e responsiva
5. Auditoria completa de todas ações
6. Testes completos: 15 testes passando
7. Integração perfeita com sistema existente

---

### 05/11/2024 - FASE 8 Completa (23:30)
- ✅ Sistema completo de histórico e métricas implementado
- ✅ 2 views criadas (historico_view, metricas_view)
- ✅ 1 form criado (HistoricoFiltrosForm)
- ✅ 2 templates criados (historico.html, metricas.html)
- ✅ 2 URLs adicionadas (historico/, metricas/)
- ✅ Navbar atualizado com novos links acessíveis por todos

**Arquivos criados**:
- templates/historico.html: Histórico completo com filtros avançados
- templates/metricas.html: Dashboard de métricas com seletor de período
- tests/test_historico_metricas.py: 16 testes completos (forms + views + utils)

**Arquivos atualizados**:
- apps/core/forms.py: HistoricoFiltrosForm adicionado
- apps/core/views.py: 2 views adicionadas (historico_view, metricas_view)
- apps/core/utils.py: calcular_metricas_periodo() adicionado
- pmcell_settings/urls.py: 2 URLs adicionadas para histórico e métricas
- templates/base.html: Links "Histórico" e "Métricas" adicionados ao navbar

**Funcionalidades implementadas**:
1. Histórico com filtros: período (data_inicio/fim), vendedor (dropdown + "Todos"), status
2. Paginação: 20 pedidos por página com navegação Anterior/Próxima
3. Apenas pedidos ativos (deletado=False) são exibidos
4. Métricas: total pedidos, finalizados, taxa conclusão, tempo médio separação
5. Itens em compra: quantidade total + percentual
6. Pedidos por status: distribuição detalhada
7. Seletor de período: 7, 30, 90 dias ou customizado
8. Botão "Atualizar Métricas" (POST - recalcula sem WebSocket)
9. Interface responsiva com Tailwind CSS
10. Auditoria completa de visualizações

**Decisões de implementação**:
1. Histórico: filtro vendedor com dropdown (todos vendedores ativos + "Todos")
2. Apenas pedidos ativos no histórico (deletado=False)
3. Paginação: 20 por página (adequado para o volume do negócio)
4. Métricas: período padrão 30 dias (customizável: 7, 30, 90 ou custom)
5. Atualização manual via botão POST (sem WebSocket para economizar recursos)
6. Acesso universal: histórico e métricas para todos usuários logados
7. Cálculo de tempo útil considera horário comercial (7:30-17h, seg-sex)

**Conquistas da FASE 8**:
1. Sistema completo de histórico com filtros avançados e paginação
2. Dashboard de métricas com indicadores essenciais
3. Função calcular_metricas_periodo() reutilizável
4. Navbar atualizado e acessível
5. Testes completos: 16 testes passando (100% de sucesso)
6. Interface moderna e consistente com o resto do sistema
7. Zero bugs detectados nos testes

---

**Próxima ação**: Iniciar FASE 9 - Ajustes e Polimento