# Configuração do PostgreSQL no Railway - PMCell

## 🎯 Problema Identificado

O projeto estava usando SQLite (`db.sqlite3`) que:
- Está no `.gitignore` (não é versionado no Git)
- É perdido a cada deploy no Railway (sistema de arquivos efêmero)
- **Resultado**: Todos os pedidos e dados desaparecem após cada push/deploy

## ✅ Solução: PostgreSQL Persistente no Railway

O PostgreSQL resolve o problema porque:
- É um banco de dados em servidor separado (não depende do filesystem)
- Persiste dados entre deploys
- É gratuito no Railway (até 5GB)
- O projeto já está preparado (tem `psycopg2-binary` instalado)

---

## 📋 Passo a Passo para Configurar PostgreSQL

### 1️⃣ Criar Banco PostgreSQL no Railway

1. Acesse o [Railway Dashboard](https://railway.app)
2. Entre no seu projeto **PMCell**
3. Clique em **"+ New"** → **"Database"** → **"Add PostgreSQL"**
4. O Railway criará automaticamente um banco PostgreSQL

### 2️⃣ Obter a URL de Conexão

1. Clique no serviço PostgreSQL criado
2. Vá na aba **"Variables"**
3. Copie o valor da variável `DATABASE_URL`
   - Formato: `postgresql://postgres:senha@região.railway.app:porta/railway`
   - Exemplo: `postgresql://postgres:abc123@monorail.proxy.rlwy.net:12345/railway`

### 3️⃣ Configurar Variável no Serviço Web

1. Volte para o serviço principal do projeto (web/API)
2. Vá em **"Variables"**
3. Adicione ou edite a variável:
   - **Nome**: `DATABASE_URL`
   - **Valor**: Cole a URL copiada do PostgreSQL
4. Clique em **"Add"** ou **"Update"**

**Importante**: O Railway pode oferecer uma "Reference Variable" que conecta automaticamente. Se disponível, use essa opção que é mais segura.

### 4️⃣ Redeploy do Serviço

1. O Railway detectará a mudança de variável
2. Fará um novo deploy automaticamente
3. O `Procfile` executará as migrations no PostgreSQL:
   ```bash
   python manage.py migrate && ...
   ```

### 5️⃣ Importar Dados Existentes (Opcional)

Se você tinha dados no SQLite local que deseja manter:

```bash
# 1. Certifique-se que o backup_data.json existe
ls backup_data.json

# 2. Configure DATABASE_URL localmente para o PostgreSQL do Railway
export DATABASE_URL="postgresql://postgres:senha@...railway.app:porta/railway"

# 3. Ative o ambiente virtual
source venv/bin/activate

# 4. Execute as migrations
python manage.py migrate

# 5. Importe os dados
python manage.py loaddata backup_data.json
```

---

## 🧪 Verificação

### Testar Persistência de Dados

1. **Acesse sua aplicação no Railway**
   ```
   https://seu-projeto.up.railway.app
   ```

2. **Crie um pedido de teste**
   - Faça login
   - Crie um novo pedido
   - Anote os detalhes

3. **Force um novo deploy**
   ```bash
   git commit --allow-empty -m "test: verificar persistência PostgreSQL"
   git push
   ```

4. **Aguarde o deploy completar**
   - Veja os logs no Railway

5. **Verifique os dados**
   - Acesse a aplicação novamente
   - O pedido deve ainda estar lá! ✅

---

## 🔍 Verificar Configuração Atual

### Verificar Variáveis no Railway

1. Dashboard → Seu Projeto → Serviço Web
2. Aba "Variables"
3. Deve ter:
   - `DATABASE_URL` → Apontando para PostgreSQL
   - `SECRET_KEY` → Chave secreta Django
   - `ALLOWED_HOSTS` → Domínios permitidos

### Verificar Logs de Deploy

```bash
# No Railway Dashboard, aba "Deployments"
# Procure por:
- "Running migrations"
- "Operations to perform: ..."
- "Applying core.0001_initial... OK"
```

### Conectar ao PostgreSQL (para debug)

```bash
# Via Railway CLI
railway connect postgres

# Ou use a URL diretamente
psql $DATABASE_URL
```

Comandos úteis no PostgreSQL:
```sql
-- Ver todas as tabelas
\dt

-- Ver pedidos
SELECT * FROM core_pedido;

-- Ver usuários
SELECT id, nome, tipo FROM core_usuario;

-- Sair
\q
```

---

## 📝 Estrutura de Arquivos Atualizada

```
pmcell/
├── db.sqlite3                    # ❌ Não é mais usado em produção
├── backup_data.json              # ✅ Backup dos dados do SQLite
├── pmcell_settings/
│   └── settings.py               # ✅ Já configurado com dj_database_url
├── .env.example                  # ✅ Template de variáveis
└── RAILWAY_POSTGRES_SETUP.md     # 📚 Este arquivo
```

---

## ⚙️ Como Funciona

### Settings.py

O arquivo `pmcell_settings/settings.py` já está configurado corretamente:

```python
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',  # Fallback para dev local
        conn_max_age=600,
        conn_health_checks=True,
    )
}
```

**Comportamento**:
- Se `DATABASE_URL` existe (Railway): usa PostgreSQL
- Se não existe (dev local): usa SQLite

### Procfile

```procfile
web: python manage.py migrate && python manage.py collectstatic --noinput && daphne -b 0.0.0.0 -p $PORT pmcell_settings.asgi:application
```

A cada deploy:
1. **migrate**: Aplica migrations no banco configurado
2. **collectstatic**: Coleta arquivos estáticos
3. **daphne**: Inicia servidor ASGI

---

## 🐛 Troubleshooting

### Erro: "FATAL: password authentication failed"

**Causa**: URL do PostgreSQL incorreta

**Solução**:
1. Copie novamente a `DATABASE_URL` do serviço PostgreSQL no Railway
2. Cole exatamente como está nas variáveis do serviço web
3. Redeploy

### Erro: "relation does not exist"

**Causa**: Migrations não foram executadas

**Solução**:
1. Verifique os logs de deploy
2. Certifique-se que `python manage.py migrate` foi executado
3. Se necessário, force um redeploy

### Dados ainda desaparecem

**Causa**: Variável `DATABASE_URL` não está configurada corretamente

**Verificação**:
```bash
# No Railway, serviço web, aba Variables
# DATABASE_URL deve começar com:
postgresql://
# E NÃO:
sqlite:///
```

### Preciso resetar o banco

```bash
# Conecte ao PostgreSQL
railway connect postgres

# Delete todas as tabelas
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
\q

# Redeploy (migrations serão aplicadas novamente)
git commit --allow-empty -m "chore: force migration rebuild"
git push
```

---

## 📊 Benefícios da Migração

| Antes (SQLite) | Depois (PostgreSQL) |
|----------------|---------------------|
| ❌ Dados perdidos a cada deploy | ✅ Dados persistentes |
| ❌ Não escalável | ✅ Escalável para produção |
| ❌ Filesystem efêmero | ✅ Banco dedicado |
| ❌ Sem backups automáticos | ✅ Backups do Railway |
| ⚠️ Bom para desenvolvimento | ✅ Pronto para produção |

---

## 🎓 Próximos Passos (Opcional)

1. **Configurar Backups Automáticos**
   - Railway Pro tem backups automáticos
   - Ou use `pg_dump` agendado

2. **Monitoramento**
   - Configure alertas de uso do banco
   - Monitore performance de queries

3. **Otimizações**
   - Adicione índices em campos frequentemente consultados
   - Configure connection pooling (já ativado com `conn_max_age=600`)

---

## 📞 Suporte

- **Railway Docs**: https://docs.railway.app/databases/postgresql
- **Django + PostgreSQL**: https://docs.djangoproject.com/en/4.2/ref/databases/#postgresql-notes
- **dj-database-url**: https://github.com/jazzband/dj-database-url

---

## ✅ Checklist Final

- [ ] PostgreSQL criado no Railway
- [ ] `DATABASE_URL` configurada no serviço web
- [ ] Deploy realizado com sucesso
- [ ] Migrations aplicadas (verificar logs)
- [ ] Pedido de teste criado
- [ ] Novo deploy não apaga os dados
- [ ] Backup dos dados antigos salvo em `backup_data.json`

**Status**: Se todos os itens estão marcados, a migração foi concluída com sucesso! 🎉
