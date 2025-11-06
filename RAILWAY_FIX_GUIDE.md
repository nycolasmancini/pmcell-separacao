# Guia Rápido: Fix para Railway

## 🚨 Problema

O JavaScript `pedido_detalhe.js` retorna **404 em produção**, impedindo que a funcionalidade de separação funcione.

---

## ✅ Solução (3 minutos)

### Opção 1: Via Railway Dashboard (RECOMENDADO)

#### Passo 1: Configurar Build Command

1. Acesse: https://railway.app/dashboard
2. Selecione seu projeto PMCELL
3. Vá em **Settings** → **Deploy**
4. Em **Build Command**, adicione:

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

5. Clique em **Save**

#### Passo 2: Verificar Start Command

Em **Start Command**, deve estar:

```bash
gunicorn pmcell_settings.wsgi:application --bind 0.0.0.0:$PORT
```

Ou se usar Daphne (para WebSocket):

```bash
daphne -b 0.0.0.0 -p $PORT pmcell_settings.asgi:application
```

#### Passo 3: Redeploy

1. Vá na aba **Deployments**
2. Clique em **Deploy** (redeploy do último commit)
3. Aguarde o deploy completar (~2-3 minutos)

---

### Opção 2: Via Código (alternativa)

Se a Opção 1 não funcionar, adicione Whitenoise:

#### 1. Adicionar ao requirements.txt

```txt
whitenoise==6.6.0
```

#### 2. Configurar em settings.py

```python
# pmcell_settings/settings.py

# Middleware - ORDEM IMPORTA!
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ← ADICIONAR AQUI
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # ... resto dos middlewares
]

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Whitenoise storage
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

#### 3. Commit e Push

```bash
git add requirements.txt pmcell_settings/settings.py
git commit -m "Add Whitenoise for static files in production"
git push origin main
```

Railway fará deploy automaticamente.

---

## 🔍 Verificar se Funcionou

Após o deploy:

### 1. Teste Manual Rápido

1. Abra: https://web-production-312d.up.railway.app/pedidos/1/
2. Faça login: 1000 / 1234
3. Abra DevTools (F12) → Console
4. **Deve ver**: `Inicializando pedido_detalhe app para pedido: 1`
5. **NÃO deve ver**: `Alpine Expression Error: pedidoDetalheApp is not defined`

### 2. Teste Checkbox

1. Clique em um checkbox
2. Confirme o dialog
3. **Deve ver**:
   - ✅ Linha fica verde
   - ✅ Badge "Separado" aparece
   - ✅ Contador aumenta

### 3. Teste Automático

```bash
cd /Users/nycolasmancini/Desktop/pmcell
source venv/bin/activate
PMCELL_LOGIN=1000 PMCELL_PIN=1234 python test_production.py
```

**Deve ver**:
```
✅ Alpine.js inicializado corretamente
✅ Script pedido_detalhe.js encontrado no HTML
✅ COR DA LINHA MUDOU
✅ BADGE 'Separado' APARECEU
✅ CHECKBOX PERMANECE MARCADO
```

---

## 🐛 Troubleshooting

### Problema: Ainda retorna 404

**Verificar logs do Railway**:

1. Railway Dashboard → seu projeto
2. Aba **Deployments** → último deploy
3. Clique em **View Logs**
4. Procure por:
   ```
   Collecting static files...
   X static files copied to 'staticfiles'
   ```

Se não aparecer, o collectstatic não rodou.

### Problema: Erro no collectstatic

**Erro comum**:
```
ValueError: Missing staticfiles manifest entry for 'js/pedido_detalhe.js'
```

**Solução**:
```python
# Em settings.py, temporariamente:
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Após collectstatic funcionar, volte para:
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

### Problema: Whitenoise não funciona

**Verifique em settings.py**:

```python
# DEBUG deve ser False em produção
DEBUG = False

# ALLOWED_HOSTS deve incluir railway
ALLOWED_HOSTS = [
    'web-production-312d.up.railway.app',
    '.railway.app',
]
```

---

## 📁 Estrutura Esperada

Após collectstatic, no servidor deve existir:

```
/app/
  ├── static/
  │   └── js/
  │       └── pedido_detalhe.js  ← Arquivo original
  └── staticfiles/
      └── js/
          └── pedido_detalhe.js  ← Arquivo coletado (servido)
```

---

## ⚡ Solução Emergencial (temporária)

Se nada funcionar, use CDN temporariamente:

1. Faça upload do `pedido_detalhe.js` para um CDN (ex: jsDelivr via GitHub)
2. Em `pedido_detalhe.html`, mude:

```html
<!-- De: -->
<script defer src="{% static 'js/pedido_detalhe.js' %}"></script>

<!-- Para: -->
<script defer src="https://cdn.jsdelivr.net/gh/SEU_USER/pmcell/static/js/pedido_detalhe.js"></script>
```

**⚠️ Isso é apenas temporário!** Use apenas para emergência.

---

## ✅ Checklist Final

Antes de considerar resolvido:

- [ ] Build command configurado no Railway
- [ ] Deploy executado com sucesso
- [ ] Logs mostram "X static files copied"
- [ ] Teste manual confirma JavaScript carregando
- [ ] Checkbox funciona (marca item como separado)
- [ ] Linha muda de cor
- [ ] Badge aparece
- [ ] Contador atualiza
- [ ] Teste automatizado passa

---

## 🎯 TL;DR

1. **Railway Dashboard** → Settings → Build Command
2. Adicionar: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
3. **Redeploy**
4. **Testar** no site

**Tempo estimado**: 3-5 minutos

---

## 📞 Suporte

Se continuar com problemas:

1. Verifique logs do Railway
2. Execute teste local: `python manage.py collectstatic`
3. Confirme que arquivo existe: `ls -lh static/js/pedido_detalhe.js`
4. Revise relatório completo: `PRODUCTION_TEST_REPORT.md`
