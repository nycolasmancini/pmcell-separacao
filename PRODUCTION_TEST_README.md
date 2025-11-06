# Teste de Produção - PMCELL

## Sobre o Teste

Script automatizado com Playwright para testar a funcionalidade de atualização de status de items no site de produção: **web-production-312d.up.railway.app**

## Como Usar

### Opção 1: Com Credenciais Padrão (1000/1000)
```bash
source venv/bin/activate
python test_production.py
```

### Opção 2: Com Credenciais Customizadas
```bash
source venv/bin/activate
PMCELL_LOGIN=1234 PMCELL_PIN=5678 python test_production.py
```

### Opção 3: Com Order ID Específico
```bash
source venv/bin/activate
PMCELL_LOGIN=1234 PMCELL_PIN=5678 PMCELL_ORDER_ID=5 python test_production.py
```

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `PMCELL_LOGIN` | `1000` | Número de login (4 dígitos) |
| `PMCELL_PIN` | `1000` | PIN do usuário (4 dígitos) |
| `PMCELL_ORDER_ID` | `1` | ID do pedido para testar |

## O que o Teste Faz

1. **Navegação**: Acessa o site de produção
2. **Login**: Faz login com as credenciais fornecidas
3. **Busca Pedido**: Procura um pedido pendente ou usa o ID fornecido
4. **Verifica JavaScript**: Checa se Alpine.js e pedido_detalhe.js carregaram
5. **Testa Checkbox**: Clica em um checkbox para marcar item como separado
6. **Verifica Mudanças**:
   - Cor da linha muda para verde?
   - Badge "Separado" aparece?
   - Contador atualiza?
   - Checkbox permanece marcado?
7. **Screenshots**: Captura screenshots de cada etapa

## Screenshots

Todos os screenshots são salvos em `test_screenshots/` com timestamp:

- `01_homepage.png` - Página inicial
- `02_login_page.png` - Página de login
- `03_login_filled.png` - Formulário preenchido
- `04_dashboard.png` - Dashboard após login
- `05_order_details.png` - Detalhes do pedido
- `06_javascript_check.png` - Verificação do JavaScript
- `07_before_checkbox_click.png` - Antes de clicar no checkbox
- `08_after_checkbox_click.png` - Depois de clicar no checkbox
- `09_menu_opened.png` - Menu aberto
- `10_final_state.png` - Estado final
- `ERROR_state.png` - Em caso de erro

## Resultados Esperados

### ✅ Teste Bem-Sucedido

Você verá estas mensagens:

```
✅ Login bem-sucedido!
✅ Alpine.js inicializado corretamente
✅ Script pedido_detalhe.js encontrado no HTML
✅ COR DA LINHA MUDOU (esperado: verde claro)
✅ BADGE 'Separado' APARECEU
✅ CHECKBOX PERMANECE MARCADO
✅ CONTADOR SEPARADOS: 1
```

### ❌ Teste com Problemas

Possíveis erros:

```
❌ Login falhou - verificar credenciais
❌ Alpine.js NÃO inicializado - JavaScript pode não estar carregando
❌ Script pedido_detalhe.js NÃO encontrado
❌ Cor da linha NÃO mudou
❌ Badge 'Separado' NÃO apareceu
```

## Resultado da Última Execução

### Tentativa com Login 1000/PIN 1000

**Status**: ❌ FALHOU - Login inválido

**Observações**:
- Site de produção está acessível
- Página de login carrega corretamente
- Credenciais 1000/1000 não são válidas em produção

**Console Logs Capturados**:
```
🖥️  Console: cdn.tailwindcss.com should not be used in production
🖥️  Console: Failed to load resource: the server responded with a status of 404 ()
```

**Screenshots Capturados**: ✅ 4 screenshots salvos em `test_screenshots/`

## Próximos Passos

Para completar o teste, você precisa:

1. **Fornecer credenciais válidas** do ambiente de produção
2. **Executar o teste novamente** com:
   ```bash
   PMCELL_LOGIN=XXXX PMCELL_PIN=YYYY python test_production.py
   ```

## Análise Preliminar do Site

Baseado nos logs do console capturados:

### ⚠️ Avisos Encontrados

1. **Tailwind CSS em Produção**
   ```
   cdn.tailwindcss.com should not be used in production
   ```
   **Recomendação**: Instalar Tailwind CSS como dependência e compilar para produção

2. **Recurso 404**
   ```
   Failed to load resource: the server responded with a status of 404
   ```
   **Possível Causa**:
   - Arquivo estático não encontrado
   - Pode ser o `pedido_detalhe.js` ou outro recurso
   - Precisa investigar qual recurso está falhando

### ✅ Funcionando

- Site carrega
- Página de login renderiza
- Formulários funcionam
- Redirecionamento funciona

## Debugging

Se o teste falhar após o login, verifique:

1. **JavaScript não carrega**:
   - Verificar se static files foram coletados no servidor
   - Verificar STATIC_URL e STATIC_ROOT nas configurações
   - Verificar se `pedido_detalhe.js` existe em produção

2. **Erros 404**:
   - Abrir Network tab no DevTools
   - Identificar qual arquivo está falhando
   - Verificar configuração de staticfiles

3. **JavaScript carrega mas não funciona**:
   - Abrir Console tab no DevTools
   - Procurar por erros JavaScript em vermelho
   - Verificar se Alpine.js está inicializando

## Comandos Úteis

### Ver screenshots capturados
```bash
open test_screenshots/
```

### Limpar screenshots antigos
```bash
rm -rf test_screenshots/
```

### Executar teste com mais verbosidade
```bash
PMCELL_LOGIN=XXXX PMCELL_PIN=YYYY python test_production.py 2>&1 | tee test_output.log
```

## Suporte

Se continuar tendo problemas:

1. Verifique os screenshots em `test_screenshots/`
2. Revise os logs do console capturados
3. Teste manualmente no navegador
4. Verifique se a correção foi deployada em produção:
   ```bash
   # No servidor de produção
   git log -1 --oneline
   # Deve mostrar: Fix: Resolve item status update functionality
   ```

---

**Nota**: Este teste requer que a correção (`{% block extra_head %}`) esteja deployada no ambiente de produção.
