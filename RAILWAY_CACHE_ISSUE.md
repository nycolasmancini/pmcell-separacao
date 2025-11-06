# Railway Static Files Cache Issue - CRITICAL

**Date**: 2025-11-06
**Status**: ⚠️ **BLOCKER** - JavaScript fix not deploying to production
**Commits Affected**: a97090e, ea36000

---

## 🔴 PROBLEM

The critical JavaScript fix (`window.pedidoDetalheApp = pedidoDetalheApp`) is NOT reaching production despite multiple deploys.

### Evidence:

```bash
# Local file (correct)
$ wc -c static/js/pedido_detalhe.js
27416 static/js/pedido_detalhe.js  # ✅ Has the fix

# Production file (old/cached)
$ curl -sI https://web-production-312d.up.railway.app/static/js/pedido_detalhe.js | grep content-length
content-length: 27313  # ❌ Missing 103 bytes (the fix)

# File timestamp
last-modified: Thu, 06 Nov 2025 00:31:10 GMT  # Hours ago, not recent!
```

### What We Tried:

1. ✅ **Added `window.pedidoDetalheApp`** to JavaScript (commit a97090e)
2. ✅ **Modified `nixpacks.toml`** to clear cache before collectstatic (commit ea36000)
3. ✅ **Waited 5+ minutes** for deploy to complete
4. ❌ **Files still cached** in production

---

##  ROOT CAUSE

Railway/Whitenoise is serving **cached/compressed** static files that were built hours ago. The build process is collecting the new files, but the **serving layer** is not picking them up.

Possible causes:
1. **Whitenoise's compressed file cache** (`staticfiles/*.gz` files)
2. **Railway's CDN/edge cache**
3. **Browser cache** (unlikely, tested with curl)
4. **Build cache persistence** between deploys

---

## 💡 SOLUTION OPTIONS

### Option 1: Manual Railway Cache Clear (RECOMMENDED)

1. Go to Railway dashboard
2. Navigate to your project settings
3. Look for "Clear Build Cache" or "Clear Deployment Cache"
4. Trigger a fresh deploy
5. Verify: `curl -sI https://web-production-312d.up.railway.app/static/js/pedido_detalhe.js | grep content-length`
   - Should show: `content-length: 27416` (or similar, larger than 27313)

### Option 2: Force Versioned Static Files

Modify `pmcell_settings/settings.py`:

```python
# Force new URL for static files by adding version parameter
STATIC_URL = '/static/'
# Add this:
import time
STATIC_VERSION = str(int(time.time()))  # Unix timestamp
# Use in templates: {% static 'js/pedido_detalhe.js' %}?v={{ STATIC_VERSION }}
```

This bypasses cache by changing the URL.

### Option 3: Disable WhiteNoise Compression (temporary)

Modify `pmcell_settings/settings.py`:

```python
# BEFORE (line 151)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# AFTER
STATICFILES_STORAGE = 'whitenoise.storage.StaticFilesStorage'  # No compression/manifest
```

Then commit and push. This prevents caching of compressed versions.

### Option 4: Use Railway's Static Files Service

Instead of serving static files through Django/Whitenoise:
1. Upload static files to Railway's static files service
2. Configure `STATIC_URL` to point to Railway's CDN
3. Ensures fresh files on every deploy

---

## 🎯 WHAT THE FIX DOES

When the fix finally deploys, it will:

1. **Make `pedidoDetalheApp()` function globally available** to Alpine.js templates
2. **Resolve all 16 Alpine.js errors**:
   - `pedidoDetalheApp is not defined`
   - `itemsSeparados is not defined`
   - `modalSubstituir is not defined`
   - `modalCompra is not defined`
   - `handleCheckboxChange is not defined`

3. **Restore full functionality**:
   - ✅ Checkboxes mark items as "separado"
   - ✅ Row colors change to green
   - ✅ Status badges appear
   - ✅ Database updates work
   - ✅ Modals for "Compra" and "Substituir" work

---

## 📊 CURRENT STATUS

| Item | Local | Production | Status |
|------|-------|------------|--------|
| **Template block** | ✅ Fixed | ✅ Deployed | Working |
| **DEBUG setting** | ✅ Fixed | ✅ Deployed | Working |
| **STATICFILES_STORAGE** | ✅ Fixed | ✅ Deployed | Working |
| **Script in extra_js** | ✅ Fixed | ✅ Deployed | Working |
| **window.pedidoDetalheApp** | ✅ Fixed | ❌ **NOT Deployed** | **BLOCKED** |

---

## 🚀 NEXT STEPS

1. **Immediate**: Try **Option 1** (Clear Railway cache)
2. **If Option 1 fails**: Try **Option 3** (Disable compression temporarily)
3. **Test**: `curl https://web-production-312d.up.railway.app/static/js/pedido_detalhe.js | grep window.pedidoDetalheApp`
   - Should return: `window.pedidoDetalheApp = pedidoDetalheApp;`
4. **Verify**: Run Playwright test
   - Should show: 0 Alpine.js errors (was 16)
   - Should show: Checkboxes working

---

## 📝 SUMMARY FOR RAILWAY SUPPORT

If you need to contact Railway support:

> "Our Django application's static files are not updating despite successful deploys. The collectstatic command runs successfully in nixpacks build phase, but Whitenoise continues serving old cached/compressed versions. We've tried:
> - Adding `rm -rf staticfiles/*` before collectstatic
> - Using `--clear` flag
> - Waiting 5+ minutes for deploy
>
> File evidence:
> - Local file: 27416 bytes
> - Production file: 27313 bytes (old)
> - Last-Modified header shows hours-old timestamp
>
> Please help us clear the static files cache or explain how to force Railway to serve fresh static files."

---

**Created**: 2025-11-06 14:38
**Last Updated**: 2025-11-06 14:38
**Status**: Awaiting Railway cache clear
