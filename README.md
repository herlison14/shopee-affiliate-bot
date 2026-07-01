# ShopeeViral.AI

SaaS para afiliados Shopee no Brasil: gera campanhas com legenda e hashtags via IA, rastreia comissões de vendas e publica conteúdo viral.

## Stack

- **Backend**: FastAPI + SQLAlchemy (async) + PostgreSQL + Alembic — `backend/`
- **Frontend**: React 18 + Vite + Tailwind CSS — `frontend/`
- **Deploy backend**: Render (free tier)
- **Deploy frontend**: Vercel

## Backend — desenvolvimento local

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements-dev.txt
cp ../.env.example .env        # ajuste DATABASE_URL e demais chaves
alembic upgrade head
uvicorn app:app --reload
```

API disponível em `http://localhost:8000`, docs em `http://localhost:8000/docs`.

### Testes

```bash
cd backend
pytest
```

## Frontend — desenvolvimento local

```bash
cd frontend
npm install
cp .env.example .env.local     # ajuste VITE_API_URL
npm run dev
```

Disponível em `http://localhost:5173`.

## Deploy

### Backend (Render)

Serviço configurado via `render.yaml`:
- Root directory: `backend`
- Build: `pip install -r requirements.txt`
- Start: `alembic upgrade head && uvicorn app:app --host 0.0.0.0 --port $PORT`
- Banco PostgreSQL free linkado via `DATABASE_URL`

Variáveis de ambiente a configurar no dashboard do Render: `SECRET_KEY`, `ANTHROPIC_API_KEY`, `SHOPEE_CONSUMER_KEY`, `SHOPEE_CONSUMER_SECRET`, `SHOPEE_REDIRECT_URI`, `FRONTEND_URL`.

### Frontend (Vercel)

- **App em produção**: https://frontend-chi-blond-wwm5qsco37.vercel.app
- **Root Directory: `frontend`** — configuração no **painel da Vercel** (Settings → Build and Deployment → Root Directory). ⚠️ **Obrigatório e fácil de esquecer**: se ficar na raiz do repo, a Vercel detecta o bot Python antigo (`requirements.txt` da raiz), instala `pandas`/`streamlit`/etc. e o build falha com `vite build ... exit 127` (`vite: not found`), mesmo com o `npm run build` passando localmente.
- Framework: Vite
- `installCommand: npm install --include=dev` (no `frontend/vercel.json`) — garante as devDependencies no build.
- Variável: `VITE_API_URL=https://shopee-viral-api.onrender.com/api/v1`

## Estrutura

```
backend/
  app.py            # FastAPI app
  config.py         # Settings (pydantic-settings)
  database.py       # Engine async + sessão
  models/           # User, Campaign, Commission
  routers/          # auth, campaigns, webhooks
  services/         # Shopee OAuth, IA (Claude), pagamentos
  alembic/          # Migrations
frontend/
  src/
    pages/          # LoginPage, DashboardPage
    hooks/          # useAuth, useCampaigns
    lib/api.js      # Cliente HTTP (axios + JWT)
```

## Modelo de negócio

MVP gratuito com comissão de 10% sobre vendas geradas pelos afiliados.
