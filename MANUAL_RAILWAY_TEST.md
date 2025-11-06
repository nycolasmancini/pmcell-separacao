# Manual Railway Production Test Guide

## Purpose
Verify that the HTTP 500 error when unchecking separated items has been fixed in Railway production.

## Hotfix Applied (Commit 0a1870e)
- Fixed `AttributeError` when accessing `request.user.nome` in unseparar/separar endpoints
- Implemented safe user access pattern with getattr/hasattr

## Test Steps

### 1. Access Railway Production
URL: https://web-production-312d.up.railway.app/

### 2. Login
- Enter your 4-digit login number
- Enter your 4-digit PIN
- Click "Entrar"

### 3. Navigate to a Pedido
- From the dashboard, click on any pedido from the list
- You'll be on the pedido detail page with a table of items

### 4. Test Separate/Unseparate Cycle
Follow these steps and verify no errors occur:

#### Step A: Separate an Item (Check)
1. Find an item with an UNCHECKED checkbox (status: Pendente)
2. **Click the checkbox** to mark it as separated
3. **Expected result**:
   - Checkbox should be checked immediately (no confirmation dialog)
   - Row should turn light green (`row-separated` class)
   - Status badge should show "Separado" (green)
   - Statistics should update
   - **NO console errors**

#### Step B: Unseparate the Item (Uncheck) - THIS IS THE FIX
1. **Click the same checkbox again** to uncheck it
2. **Expected result**:
   - Checkbox should be unchecked
   - Row should return to normal (no green background)
   - Status badge should show "Pendente" (gray)
   - Statistics should update
   - **NO HTTP 500 error**
   - **NO console errors** (except Tailwind CDN warning which is harmless)

#### Step C: Verify Console (CRITICAL)
Open browser DevTools (F12) → Console tab

**Before the fix**, you would see:
```
[UNCHECK] Enviando requisição para desseparar item X...
Failed to load resource: the server responded with a status of 500 (unseparar, line 0)
```

**After the fix**, you should see:
```
[UNCHECK] Enviando requisição para desseparar item X...
[UNCHECK] ✓ Item X desseparado com sucesso
```

### 5. Test Multiple Cycles
Repeat the check/uncheck cycle 3-4 times to ensure stability:
1. Check → Uncheck → Check → Uncheck
2. Each operation should work smoothly with no errors

### 6. Test with Substituted Item (Optional)
1. Find an item with status "Substituído" (blue badge)
2. Click the checkbox (it should already be checked)
3. **Expected result**: Item remains checked, shows message that substituted items cannot be unseparated
4. Substituted items should remain marked as separated

### 7. Test with "Em Compra" Item (Optional)
1. Find an item with status "Em Compra" (yellow badge)
2. Checkbox should be unchecked
3. Click to check it
4. **Expected result**: Item transitions from "Em Compra" → "Separado" (green)

## Success Criteria

✅ **Fix is successful if:**
1. Unchecking separated items works without HTTP 500 error
2. Console shows success messages instead of HTTP 500 errors
3. UI updates correctly (checkbox, row styling, badges, statistics)
4. Multiple check/uncheck cycles work smoothly
5. Real-time WebSocket updates work (if testing with multiple users)

❌ **Fix failed if:**
1. HTTP 500 error appears in console when unchecking
2. Server returns HTML error page instead of JSON response
3. Checkbox state doesn't update
4. Console shows AttributeError logs

## Environment Info
- **Railway URL**: https://web-production-312d.up.railway.app/
- **Commit**: 0a1870e (hotfix: Fix AttributeError in separar/unseparar endpoints)
- **Files Changed**: apps/core/views.py (lines 713, 740, 746, 840)
- **Pattern Used**: `getattr(request.user, 'nome', 'anonymous') if hasattr(request.user, 'is_authenticated') and request.user.is_authenticated else 'anonymous'`

## Automated Testing (Optional)

If you have Railway credentials, you can run automated tests:

```bash
# Set credentials as environment variables
export RAILWAY_NUMERO_LOGIN="1234"  # Your 4-digit login number
export RAILWAY_PIN="5678"            # Your 4-digit PIN

# Run Railway production tests
source venv/bin/activate
pytest tests/test_railway_unseparate_fix.py -v --headed

# This will:
# - Login to Railway production
# - Find a pedido with items
# - Test separate/unseparate cycle
# - Monitor for HTTP 500 errors
# - Verify UI updates correctly
```

## Troubleshooting

### If you still see HTTP 500 errors:
1. Check Railway deployment completed successfully
2. Verify commit 0a1870e is deployed (check Railway dashboard)
3. Check Railway logs for any startup errors
4. Try clearing browser cache and cookies
5. Try in incognito/private browsing mode

### If WebSocket errors (1006) appear:
- This is a separate issue related to Redis channel layer
- WebSocket errors don't affect the unseparate functionality
- Can be resolved by adding Redis addon to Railway

## Report Results

After testing, report:
1. ✅ or ❌ - Did unseparate work without HTTP 500?
2. Console output (screenshot or copy-paste)
3. Any unexpected behavior
4. Browser used (Chrome, Firefox, Safari, etc.)
