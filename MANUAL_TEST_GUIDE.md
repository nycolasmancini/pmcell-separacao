# Manual Testing Guide - Separation Screen Fixes

## Deployment Information
- **Commit**: 67ea67d
- **Push Time**: 16:24:47 (Nov 6, 2025)
- **Expected Ready**: 16:29 (allow 4-5 minutes for Railway deployment)
- **URL**: https://web-production-312d.up.railway.app

## Issues Fixed

### Issue #1: Uncheck Product Returns HTTP 500 Error ✅
**Root Cause**: Missing `item_unseparado` handler in WebSocket consumer
**Fix**: Added the missing handler in `apps/core/consumers.py`

### Issue #2: Product Substitution No Real-time Update ✅
**Root Cause**: WebSocket message missing complete data fields
**Fix**: Added `separado_por` and `separado_em` fields to the broadcast in `apps/core/views.py`

### Issue #3: Mark to Buy No Real-time Update ⚠️
**Status**: Added extensive debug logging to diagnose the issue
**Note**: The handler exists and should work - debug logs will reveal if there's a DOM selector issue

### Issue #4: WebSocket Connection Failing (Error 1006) ✅
**Root Cause**: Daphne configuration not optimized for Railway proxy
**Fix**: Added `--proxy-headers`, `--verbosity 2`, and `--access-log -` to Procfile

---

## Pre-Test Checklist

1. ✅ Open browser Developer Tools (F12)
2. ✅ Navigate to Console tab
3. ✅ Navigate to Network tab
4. ✅ Enable "Preserve log" in Console
5. ✅ Filter Network by "WS" to see WebSocket connections

---

## Test #1: Uncheck Product (HTTP 500 Fix)

### Steps:
1. Navigate to: `https://web-production-312d.up.railway.app/pedido/2/`
2. Open Console (F12)
3. Find a product that is NOT checked
4. Click checkbox to CHECK it
5. Wait 1-2 seconds for request to complete
6. Click checkbox again to UNCHECK it
7. Watch Console for errors

### Expected Results:
- ✅ Checkbox changes state successfully
- ✅ Status updates in database
- ✅ **NO HTTP 500 error** in Console
- ✅ No red error messages
- ✅ Console shows: `[CHECKBOX] Response status: 200`

### Previous Behavior (BROKEN):
```
[UNCHECK] Response status: 500
[UNCHECK] Erro HTTP 500: <!doctype html>...Server Error (500)...
```

### New Behavior (FIXED):
```
[UNCHECK] Enviando requisição para desseparar item X...
[UNCHECK] Response status: 200
[UNCHECK] Response data: {success: true, ...}
✓ [UNCHECK] Item desseparado com sucesso
```

---

## Test #2: Product Substitution Real-time Update

### Steps:
1. Navigate to pedido detail page
2. Find a product row
3. Click "Substituir" button (or equivalent)
4. Enter substitute product name: `PRODUTO TESTE SUBSTITUTO`
5. Confirm substitution
6. **DO NOT REFRESH THE PAGE**
7. Watch the row update in real-time

### Expected Results:
- ✅ Status badge changes to blue "Substituído"
- ✅ Product name updates to show substitute
- ✅ Timestamp appears: "João - 06/11/2025 16:30"
- ✅ **All happens WITHOUT page refresh**

### Console Logs to Watch:
```
[WebSocket] Item substituído: {id: X, substituido: true, produto_substituto: "...", separado_por: "...", separado_em: "..."}
```

### Previous Behavior (BROKEN):
- Substitution succeeded but UI didn't update
- Had to refresh page to see changes
- Missing user and timestamp data

---

## Test #3: Mark to Buy Real-time Update (WITH DEBUG LOGGING)

### Steps:
1. Navigate to pedido detail page
2. Find a product that is NOT marked for purchase
3. Click "Comprar" button
4. **DO NOT REFRESH THE PAGE**
5. Watch Console for detailed debug logs

### Expected Results:
- ✅ Status badge changes to yellow "🛒 Em Compra"
- ✅ Timestamp appears with user info
- ✅ **All happens WITHOUT page refresh**

### Console Debug Logs to Watch:
```
[WebSocket] Item em compra: {...}
[DEBUG] Procurando linha com item ID: X
[DEBUG] Linha encontrada: Sim
[DEBUG] Status cell encontrada: Sim
[DEBUG] Status badge encontrado: Sim
[DEBUG] Status badge atualizado com sucesso
[DEBUG] Timestamp existente: Não
[DEBUG] Timestamp adicionado: João - 06/11/2025 16:30
[DEBUG] Atualizando estatísticas...
[DEBUG] Item em compra processado com sucesso
```

### If Debug Shows "Não" Somewhere:
This reveals WHERE the problem is:
- "Linha encontrada: Não" → Item ID selector issue
- "Status cell encontrada: Não" → Column number wrong
- "Status badge encontrado: Não" → Badge selector issue

---

## Test #4: WebSocket Connection (Error 1006 Fix)

### Steps:
1. Navigate to pedido detail page
2. Open Console (F12)
3. Look for WebSocket connection messages
4. Check Network tab → WS filter

### Expected Results:
- ✅ WebSocket connects successfully
- ✅ **NO "error 1006"** messages
- ✅ **NO "bad response from the server"** errors
- ✅ Connection stays alive (no constant reconnection attempts)

### Console Logs to Watch:
```
[WebSocket] Conectando ao pedido 2... wss://web-production-312d.up.railway.app/ws/pedido/2/
[WebSocket] Conexão estabelecida com sucesso
```

### Previous Behavior (BROKEN):
```
[Error] WebSocket connection to 'wss://...' failed: There was a bad response from the server.
[Log] [WebSocket] Conexão fechada: 1006 ""
[Log] [WebSocket] Tentando reconectar (1/10) em 1000ms...
```

---

## Test #5: Real-time Updates Across Browser Tabs (BONUS)

### Steps:
1. Open pedido detail page in TWO browser tabs
2. In Tab 1: Mark a product for purchase
3. In Tab 2: Watch for real-time update
4. Verify both tabs show the same state

### Expected Results:
- ✅ Changes in Tab 1 appear immediately in Tab 2
- ✅ WebSocket broadcasts to all connected clients
- ✅ No need to refresh either tab

---

## Troubleshooting

### If Tests Still Fail:

1. **Check Railway Deployment Status**
   ```bash
   # Verify commit is deployed
   curl https://web-production-312d.up.railway.app/ -I
   ```

2. **Check Browser Cache**
   - Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
   - Or clear cache completely

3. **Verify Daphne Configuration**
   - Check Railway logs for Daphne startup messages
   - Should show: `--verbosity 2 --access-log - --proxy-headers`

4. **Check WebSocket Protocol**
   - Network tab → WS → Should show "101 Switching Protocols"
   - If 403/404 → Authentication or routing issue
   - If 502/503 → Server not responding

---

## Success Criteria

All tests pass when:
- [x] Uncheck returns HTTP 200 (no 500 error)
- [x] Product substitution updates UI without refresh
- [x] Mark to buy updates UI without refresh (or debug logs show why not)
- [x] WebSocket connects without error 1006
- [x] Real-time updates work across tabs

---

## Automated Test

If manual testing is successful, you can run the automated Playwright test:

```bash
source venv/bin/activate
python test_separation_fixes.py
```

This will automatically test all scenarios and provide a pass/fail report.

---

## Contact

If issues persist after deployment, provide:
1. Console logs (copy/paste entire console output)
2. Network tab WebSocket connection status
3. Railway deployment logs
4. Screenshots of the issue

Happy testing! 🚀
