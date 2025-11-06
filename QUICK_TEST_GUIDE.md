# Quick Test Guide - Status Update Fix

## The Problem (Before Fix)
- ❌ Clicking checkboxes did nothing
- ❌ Row colors didn't change
- ❌ Badges didn't appear
- ❌ Database wasn't updated

## The Solution
Added one line to `templates/base.html:18`:
```html
{% block extra_head %}{% endblock %}
```

## Quick Verification (5 minutes)

### Step 1: Start the Server
```bash
cd /Users/nycolasmancini/Desktop/pmcell
source venv/bin/activate
python manage.py runserver
```

### Step 2: Open Browser
Navigate to: `http://localhost:8000/`

### Step 3: Login
- Use login: **1000** (or any existing user)
- Enter your PIN

### Step 4: Go to Any Order
- Click on a pending order from the dashboard
- Or directly: `http://localhost:8000/pedidos/1/`

### Step 5: Open DevTools (IMPORTANT!)
- Press **F12** (or Cmd+Option+I on Mac)
- Go to **Console** tab

### Step 6: Verify JavaScript Loaded
Look for this message in console:
```
Inicializando pedido_detalhe app para pedido: X
[WebSocket] Conectando ao pedido X...
[WebSocket] Conectado com sucesso!
```

✅ **If you see these messages** → JavaScript is loading correctly!
❌ **If you DON'T see these** → JavaScript is NOT loading

### Step 7: Test Checkbox Click
1. Click any checkbox next to an item
2. Click "OK" on confirmation dialog

**Check Console - Should see:**
```javascript
[CHECKBOX] Enviando requisição para separar item X...
[CHECKBOX] Response status: 200 OK
✓ [CHECKBOX] Item separado com sucesso
```

**Check UI - Should see:**
- ✅ Row background turns **light green**
- ✅ Badge appears: "Separado" (green pill)
- ✅ Counter "Separados" increases
- ✅ Checkbox stays checked

### Step 8: Check Network Tab (DevTools)
1. Go to **Network** tab in DevTools
2. Click another checkbox
3. Look for request: `separar/?` or similar

**Should see:**
- Method: **POST**
- Status: **200 OK**
- Response: `{"success": true, ...}`

### Step 9: Verify Database (Optional)
```bash
source venv/bin/activate
python manage.py shell
```

```python
from apps.core.models import ItemPedido

# Replace 5 with the ID of item you just checked
item = ItemPedido.objects.get(id=5)
print(f"Separado: {item.separado}")  # Should be True
print(f"Separado por: {item.separado_por}")
print(f"Separado em: {item.separado_em}")
```

## Expected Results

### ✅ Working Correctly
- Console shows all log messages
- Rows change color immediately
- Badges appear
- Counters update
- Network shows successful POST requests
- Database has updated values

### ❌ Still Broken
If it's still not working:

1. **Clear browser cache** (Ctrl+Shift+Delete)
2. **Hard refresh** (Ctrl+Shift+R or Cmd+Shift+R)
3. **Check console for errors** (red messages)
4. **Verify static files collected**:
   ```bash
   python manage.py collectstatic --noinput
   ```
5. **Check file exists**:
   ```bash
   ls -lh static/js/pedido_detalhe.js
   ls -lh staticfiles/js/pedido_detalhe.js
   ```

## Visual Checklist

When you click a checkbox, within 1 second you should see ALL of these:

- [ ] Confirmation dialog appears
- [ ] After clicking OK, row turns light green
- [ ] Green "Separado" badge appears in Status column
- [ ] "Separados" counter at top increases by 1
- [ ] Console shows success message
- [ ] Network tab shows POST request with 200 status

If ALL boxes are checked → **Fix is working!** ✅

If ANY box is unchecked → Check troubleshooting steps above

## Common Issues

### Issue: "Checkbox clicks don't do anything"
**Cause**: JavaScript not loading
**Fix**:
1. Check browser console for errors
2. Verify `<script>` tag in page source (Ctrl+U)
3. Clear cache and hard refresh

### Issue: "Row doesn't change color"
**Cause**: CSS class not applied
**Fix**: Check console logs - AJAX request might be failing

### Issue: "Error 403 Forbidden"
**Cause**: CSRF token missing
**Fix**: Check for `{% csrf_token %}` in template

### Issue: "Error 404 Not Found"
**Cause**: Static files not collected
**Fix**: Run `python manage.py collectstatic`

## Quick Test Script

Run this to verify everything:
```bash
source venv/bin/activate
python test_fix_verification.py
```

Should see:
```
Tests Passed: 7/9
Success Rate: 77.8%
```

If you see this, the fix is working!

## Need Help?

1. Read `FIX_SUMMARY.md` for detailed explanation
2. Check browser console for specific error messages
3. Verify template changes in `templates/base.html:18`
4. Ensure server is running without errors

---

**Remember**: The fix was just ONE LINE added to `base.html`. Everything else was already working!
