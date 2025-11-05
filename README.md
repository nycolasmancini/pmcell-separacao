# Sistema de Separação de Pedidos - PMCELL

Sistema interno para gestão de separação de pedidos com processamento automático de PDFs e controle em tempo real.

## 🚀 Tecnologias

- Django 4.2.7
- Python 3.11
- PostgreSQL (produção) / SQLite (desenvolvimento)
- Django Channels (WebSocket - próximas fases)
- Railway (deploy)

## 📋 Status do Desenvolvimento

- [x] Deploy inicial no Railway
- [ ] Sistema de autenticação
- [ ] Modelos de dados
- [ ] Upload e processamento de PDF
- [ ] Dashboard em tempo real
- [ ] Painel de separação
- [ ] Painel de compras
- [ ] Métricas e relatórios

## 🔧 Instalação Local

1. Clone o repositório:
```bash
git clone https://github.com/[seu-usuario]/pmcell-separacao.git
cd pmcell-separacao
```

2. Crie e ative o ambiente virtual:
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Execute as migrações:
```bash
python manage.py migrate
```

5. Crie um superusuário:
```bash
python manage.py createsuperuser
```

6. Execute o servidor:
```bash
python manage.py runserver
```

Acesse: http://localhost:8000

## 🚢 Deploy no Railway

O projeto está configurado para deploy automático no Railway. Qualquer push para a branch `main` dispara um novo deploy.

### Configuração PostgreSQL

⚠️ **IMPORTANTE**: Configure o PostgreSQL no Railway para persistir dados entre deploys.

**Guia completo**: Veja [`RAILWAY_POSTGRES_SETUP.md`](RAILWAY_POSTGRES_SETUP.md)

**Passos rápidos**:
1. Adicione banco PostgreSQL no Railway Dashboard
2. Configure variável `DATABASE_URL` no serviço web
3. Redeploy (migrations serão executadas automaticamente)

### Variáveis de Ambiente (Railway)

- `DATABASE_URL`: URL de conexão do PostgreSQL (obrigatório)
- `SECRET_KEY`: Chave secreta do Django (gerada automaticamente)
- `DEBUG`: False (produção)
- `ALLOWED_HOSTS`: Configurado automaticamente

## 📁 Estrutura do Projeto

```
pmcell/
├── pmcell_settings/    # Configurações Django
├── apps/               # Aplicações (em desenvolvimento)
├── templates/          # Templates HTML
├── static/            # Arquivos estáticos
├── requirements.txt   # Dependências
├── Procfile          # Configuração Railway
├── runtime.txt       # Versão Python
└── planejamento.md   # Planejamento detalhado
```

## 👥 Tipos de Usuário

- **VENDEDOR**: Upload de PDFs e criação de pedidos
- **SEPARADOR**: Separação de itens dos pedidos
- **COMPRADORA**: Gestão de compras
- **ADMINISTRADOR**: Acesso total ao sistema

## 📊 Funcionalidades Planejadas

1. **Upload de PDF**: Processamento automático de orçamentos
2. **Separação**: Controle de itens separados em tempo real
3. **Compras**: Painel para itens que precisam ser comprados
4. **Dashboard**: Visão geral com WebSocket para atualizações em tempo real
5. **Métricas**: Relatórios de desempenho e tempo de processamento

## 🔒 Segurança

- Autenticação por número de login + PIN (4 dígitos)
- Rate limiting para tentativas de login
- Soft delete para manter histórico
- Auditoria completa de todas ações

## 📝 Licença

Sistema interno PMCELL - Uso exclusivo

---

**Versão**: 0.0.1 (Deploy Inicial)
**Última atualização**: 04/11/2024