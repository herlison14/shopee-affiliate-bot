# Shopee Affiliate Bot — Memória do Projeto

> Este repositório tem dois projetos distintos:
> 1. **ShopeeViral.AI** (`backend/` + `frontend/`) — SaaS novo, ver seção abaixo.
> 2. **Shopee Affiliate Bot** (raiz: `main.py`, `scraper/`, `dashboard/` etc.) — bot de scraping antigo, documentado no restante deste arquivo.

## ShopeeViral.AI (backend/ + frontend/)

SaaS para afiliados Shopee: gera campanhas com legenda/hashtags via IA (Claude), rastreia comissões, expõe um servidor MCP por usuário (Claude Desktop, ChatGPT) e tem uma vitrine pública por usuário.

- **Stack**: FastAPI + SQLAlchemy async + Alembic + PostgreSQL (`backend/`); React + Vite + Tailwind (`frontend/`)
- **Deploy**: Render (`backend/`, autoDeploy no push pra `main`) + Vercel (`frontend/`). App em produção: https://frontend-chi-blond-wwm5qsco37.vercel.app. ⚠️ **Na Vercel, o Root Directory tem que ser `frontend`** (config do painel, Settings → Build and Deployment) — se ficar na raiz, a Vercel detecta o bot Python antigo (`requirements.txt` da raiz) e o build falha com `vite build ... exit 127`, mesmo passando localmente
- **Agente autônomo "James"**: roda em background via APScheduler, promove rascunhos esquecidos, renova legendas sem venda, sugere replicar campanhas de sucesso — cada usuário liga/desliga em `agent_enabled`
- **Vitrine pública**: `/vitrine/:userId` no frontend, alimentada por `GET /api/v1/public/storefront/{user_id}` — só mostra campanhas com `affiliate_link` preenchido e status `posted`/`scheduled`. Cada card mostra a **miniatura do produto** (`image_url`, com fallback pro emoji 🛍️ e `onError` que esconde imagem quebrada) + seta CTA + tag "MAIS VENDIDO" nas que já venderam. Editável em "Sua vitrine pública" no dashboard
- **Integração Instagram** (Graph API — Content Publishing): `services/instagram_service.py` (fluxo oficial de 2 passos: `POST /{ig_user_id}/media` → `POST /{ig_user_id}/media_publish`) + `routers/instagram.py` (`/api/v1/instagram/connect`, `/status`, `/campaigns/{id}/publish`) + tool MCP `postar_no_instagram`. Usa `graph.facebook.com` (host correto pra publicação; **não** `graph.instagram.com`, que é a Basic Display e não publica) com o **IG Business Account ID** vinculado a uma Página do Facebook. Token de longa duração por usuário no model `User` (`instagram_access_token`/`instagram_user_id`/`instagram_token_expires_at`). Feed exige mídia → `Campaign.image_url` (migration 0008; campo opcional no form de nova campanha). Envs `INSTAGRAM_APP_ID`/`INSTAGRAM_APP_SECRET`. **Só funciona depois de o app passar pela App Review da Meta** (`instagram_content_publish` + `instagram_basic`) e a conta ser Business vinculada a uma Página do FB. Só API oficial, sem automação de navegador. **Frontend**: `hooks/useInstagram.js` + `components/InstagramSection.jsx` (seção no dashboard pra conectar conta colando token + IG Business Account ID; mostra status) e botão "Postar no Instagram" no `CampaignCard` (aparece quando a conta está conectada e a campanha tem `image_url`; mostra "✓ Publicado" com link do post). Tudo pronto, mas o publish só funciona de fato após a App Review da Meta.
- **Normalização de URL do produto** (`services/shopee_url.py`): aplicada em **todo** ponto onde uma campanha nasce (`POST /campaigns`, `/campaigns/bulk`, tool MCP `criar_campanha`). Links de oferta temporários (`shopee.com.br/offer/product_offer/{id}`) e encurtados (`s.shopee.com.br`) **expiram** e não fixam um produto — o link de afiliado gerado em cima deles quebra. A camada extrai `shop_id`/`item_id` (formatos `-i.{shop}.{item}` ou `/product/{shop}/{item}`), normaliza pra forma canônica `shopee.com.br/product/{shop}/{item}` (dedup do bulk passa a casar URLs do mesmo produto em formatos diferentes) e, quando a URL **não** fixa um produto estável, grava um aviso em `status_detail` (aparece em amber no `CampaignCard`). Não resolve links de oferta via rede (aligned com a decisão de não automatizar a Shopee) — sinaliza pro usuário trocar pela URL do produto.
- **Editar campanha**: `PATCH /api/v1/campaigns/{id}` (parcial, `exclude_unset`) edita `product_url`/`affiliate_link`/`caption`/`hashtags`; tools MCP `definir_link_afiliado` e `definir_url_produto`. Ao trocar a `product_url`, ela é normalizada e o aviso de URL instável (`status_detail`) é recalculado — dá pra consertar uma campanha que nasceu com link de oferta sem perder legenda/hashtags. No frontend, quando `status_detail` está preenchido o `CampaignCard` mostra um bloco âmbar com um campo "Corrigir URL" (chama `updateProductUrl`). No frontend, `components/CampaignCard.jsx` mostra cada campanha com fluxo manual de link: botão "Gerar link" (abre `affiliate.shopee.com.br/offer/custom_link` em nova aba) + "Copiar URL do produto" + campo pra colar o link gerado. Fluxo 100% manual, sem automação (ver decisão sobre Shopee abaixo)
- **Importar em lote**: `POST /api/v1/campaigns/bulk` cria várias campanhas de uma vez (gera legenda/hashtags por IA, dedup por `product_url`; máx. 100 itens por request — teto defensivo, cada item dispara uma chamada de IA). No frontend, `components/ImportProducts.jsx` lê CSV (colado ou arquivo) no navegador — sem dependência `xlsx` (tem vuln high sem fix; usuário salva como CSV no Excel). Colunas reconhecidas por nome: produto/nome, url_produto/url, link_afiliado (opcional)
- **PWA (instalável no celular)**: `frontend/public/manifest.webmanifest` + `sw.js` (service worker network-first, cache só de fallback — evita servir versão velha; pré-cacheia o app shell `/`+`/index.html` no install pra navegação offline de qualquer rota da SPA cair no shell) + ícones `icon-{192,512,maskable-512}.png` + meta tags no `index.html`. SW registrado em `main.jsx` só em produção. `vercel.json` tem headers de Content-Type pra `/sw.js` e `/manifest.webmanifest`, e `installCommand: npm install --include=dev` (sem isso a Vercel pulava as devDependencies no deploy e o build falhava com `vite: not found` / exit 127, mesmo passando localmente). `start_url` do app é `/dashboard`. **Prompt de instalação**: `hooks/usePwaInstall.js` (captura `beforeinstallprompt` no Android/Chrome, detecta iOS/standalone) + `components/InstallPrompt.jsx` (banner no topo do dashboard com botão "Instalar app" no Android e instruções "Adicionar à Tela de Início" no iOS; dismissível, lembra a dispensa via `localStorage`)
- **Responsividade mobile**: padding reduzido no celular (`px-4 sm:px-6`, `p-5 sm:p-6`); header do dashboard é `sticky` com e-mail truncado; utilitários `pt-safe`/`pb-safe`/`px-safe` em `index.css` (usam `env(safe-area-inset-*)`) respeitam notch/barra de gestos do iPhone em modo standalone — aplicados nos headers, no `main` e na vitrine. `viewport-fit=cover` já no `index.html`. Mínimo de senha alinhado ao backend (8 caracteres) no `LoginPage`
- **Acessibilidade (WCAG 2.1 AA)**: auditado com axe-core via Playwright (script em scratchpad, não versionado). Corrigido: `aria-label` nos inputs readonly (URL MCP e da vitrine) no dashboard, landmark `<main>` no `LoginPage` e na `StorefrontPage` (+ `.sf-main` flex pra manter o layout central), headings das features da landing `h3`→`h2` (ordem), sparkles/ícones decorativos da vitrine com `aria-hidden`. **Contraste**: cor `shopee-dark` #cc3a17 no `tailwind.config.js` pra superfícies sólidas com texto branco pequeno (botões) e badges/links de texto pequeno — passa no AA; o `shopee` #ee4d2d fica só nos títulos grandes/acentos (que passam no AA em texto grande). `text-gray-400`→`gray-500` e `text-red-500`→`red-600` nos textos secundários. **Resultado: axe-core reporta 0 violações nas 4 telas.**
- **Antes de comitar**: seguir o checklist em [CONTRIBUTING.md](./CONTRIBUTING.md) — testes do backend, build do frontend, validação pós-deploy

### Integração Instagram (publicação automática de campanhas)

Publicação de campanhas no feed do Instagram via **API oficial** (Instagram Graph API — Content Publishing). Sem automação de navegador — alinhado à decisão de só usar APIs oficiais.

**Stack**: FastAPI + React/Vite + Graph API no host `graph.facebook.com/v21.0` (configurável via env `INSTAGRAM_GRAPH_API_BASE`). **Não** `graph.instagram.com` (Basic Display, não publica). Fluxo oficial de 2 passos: `POST /{ig_user_id}/media` (cria o container com `image_url` + `caption`) → `POST /{ig_user_id}/media_publish` (publica).

**Fluxo do usuário**:
1. Dashboard → seção "Instagram" (`components/InstagramSection.jsx`) → colar **token de longa duração** + **IG Business Account ID**.
2. Backend valida com `GET /{ig_user_id}` (`services/instagram_service.get_account_info`) e guarda no `User`.
3. Criar/editar campanha com `image_url` (obrigatória pra publicar — o feed exige mídia; o usuário fornece a URL da imagem manualmente).
4. Botão "Postar no Instagram" no `CampaignCard` — aparece quando a **conta está conectada** e a campanha tem **`image_url`**.
5. `POST /api/v1/instagram/campaigns/{id}/publish` → em sucesso, `status="posted"` + `posted_url`; em falha, `status="needs_review"` + `status_detail`.

**Pré-requisitos (do usuário)**: conta Instagram Profissional/Business vinculada a uma Página do Facebook; app no Meta for Developers **tipo Business** (⚠️ **não** "Consumer" — Consumer não libera `instagram_content_publish`) com Facebook Login + Instagram Graph API; scopes `instagram_basic` + `instagram_content_publish`; token de longa duração (60 dias); IG Business Account ID.

**Pegadinhas do setup no Meta** (erros que já custaram tempo — não repetir):
- **App Review NÃO é pré-requisito pra testar.** Com a **própria conta** (admin/tester do app), publica em **modo Desenvolvimento sem App Review**. A App Review (`instagram_content_publish` + verificação de negócio, ~dias) só serve pra liberar a publicação pra **outros** usuários.
- **IG Business Account ID** não fica em "Settings → Basic". Pega no **Graph API Explorer**: `GET /me/accounts` → id da Página → `GET /{page-id}?fields=instagram_business_account` → o `id` retornado.
- **Token de longa duração**: trocar o curto em `graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=CURTO` — **não** `graph.instagram.com` (Basic Display, host errado).
- **`INSTAGRAM_APP_ID`/`INSTAGRAM_APP_SECRET` no Render são opcionais** pro fluxo atual: o `/connect` só valida o token colado (`get_account_info`), não lê essas envs. Servem só pra um futuro refresh automático de token.

**Banco** (migrations): `0008` (do main) adiciona `users.instagram_access_token`/`instagram_user_id`/`instagram_token_expires_at`; `0009` adiciona `campaigns.image_url`.

**API** (`routers/instagram.py`, protegidos por `get_current_user`): `POST /api/v1/instagram/connect`, `GET /api/v1/instagram/status`, `POST /api/v1/instagram/campaigns/{id}/publish`. **MCP**: tool `postar_no_instagram(campaign_id)`.

### Importante: automação de navegador no site da Shopee é proibitiva

A Shopee detecta automação de navegador (Playwright/CDP, extensões de automação) mesmo com
patches de stealth (mascarar `navigator.webdriver` etc.) e perfil real do Chrome — bate
CAPTCHA/verificação de novo após poucas tentativas. **Decisão**: não automatizar navegação
no site da Shopee (descoberta de produtos, geração de link, postagem) por scripts —
risco real de a conta do usuário ser restringida. `tools/automation/orchestrator.py` existe
no repo mas não deve ser usado para esse fim.

Fluxo seguro que funciona: usuário navega manualmente e exporta uma planilha Excel
(produto, preço, vendas, comissão, URL) → Claude lê a planilha → cria campanhas via MCP
automaticamente a partir daí. Link de afiliado (`Obter link`) continua sendo clicado
manualmente pelo usuário, produto por produto.

`affiliate.shopee.com.br/dashboard` tem métricas reais de comissão/pedidos (Relatório de
vendas, Relatório de cliques) que o bot antigo nunca usou — possível fonte de dados reais
de comissão no futuro, mas capturar isso também exigiria automação detectável.

Pendências e decisões de negócio (chaves Shopee, pricing) ficam na memória do Claude, não aqui.

## Sobre o projeto (bot de scraping antigo)
Bot de automação de marketing de afiliados da Shopee com geração de copy por IA, postagem automática no Shopee Videos e TikTok, e dashboard Streamlit.

## Dados do usuário
- **Nome:** Herlison
- **E-mail Shopee:** herlison14@gmail.com
- **WhatsApp:** (21) 99792-7927
- **GitHub:** https://github.com/herlison14/shopee-affiliate-bot

## Estrutura do projeto
```
shopee-affiliate-bot/
├── main.py                          # Orquestrador principal + argparse
├── config/settings.py               # Credenciais e constantes (via .env)
├── scraper/shopee_affiliate.py      # Playwright CDP — scraping afiliados
├── converter/link_converter.py      # Injeção de SubIDs nos links
├── ai/copy_generator.py             # Geração de copy via Claude API
├── scheduler/
│   ├── post_scheduler.py            # APScheduler + postagem TikTok/Shopee
│   ├── shopee_video_poster.py       # Automação Playwright para Shopee Videos
│   ├── video_downloader.py          # Download YouTube Shorts / TikTok / MP4
│   └── notifier.py                  # Notificações WhatsApp Web via CDP
├── dashboard/app.py                 # Streamlit dashboard (localhost:8501)
├── data/
│   ├── output.xlsx                  # Produtos + copy gerados
│   ├── videos/                      # Vídeos para postagem automática
│   ├── manual_queue.json            # Fila manual (sem vídeo)
│   └── .shopee_session.json         # Sessão Playwright salva
└── logs/affiliate_bot.log           # Log completo do sistema
```

## Stack técnica
- **Browser automation:** Playwright + Chrome CDP (porta 9222)
- **IA:** Anthropic Claude API (claude-opus-4-6)
- **Scheduler:** APScheduler (America/Sao_Paulo) — 09:00, 13:00, 20:00
- **Dashboard:** Streamlit >= 1.40.0 + Plotly
- **Postagem:** TikTok Content Posting API v2 + Shopee Videos via browser
- **WhatsApp:** WhatsApp Web via CDP
- **Download de vídeos:** yt-dlp (YouTube Shorts, TikTok, MP4 direto)
- **Excel:** pandas + openpyxl

## Configuração Chrome CDP
Chrome deve ser aberto com:
```
--remote-debugging-port=9222 --user-data-dir=C:\ChromeDebug
```
Arquivo: `start_chrome.bat`

## Fluxo de uso diário
1. `start_chrome.bat` → abre Chrome com CDP
2. Login em affiliate.shopee.com.br
3. `iniciar_sistema.bat` → abre dashboard em localhost:8501
4. Clicar "Executar Pipeline" → scrape + copy IA + Excel
5. Colocar vídeos em `data/videos/`
6. Bot posta automaticamente 09h/13h/20h

## Colunas do Excel (output.xlsx)
`produto | link_original | link_afiliado | preco | comissao_novo | comissao_atual | ganho_estimado | overlay | legenda | hashtags | estrategia | status_agendamento | data_publicacao`

## Status de agendamento
- `pendente` — aguardando postagem
- `publicado_tiktok` — postado no TikTok
- `publicado_shopee` — postado no Shopee Videos
- `fila_manual` — sem vídeo, copy pronto para postar manualmente
- `falhou_tiktok` / `falhou_shopee` — erro na postagem

## Scheduled Task (Claude Agent)
- **ID:** `auto-post-shopee`
- **Horário:** 09:00, 13:00, 20:00 diário
- **Função:** posta produtos pendentes automaticamente no Shopee

## Variáveis de ambiente (.env)
```
ANTHROPIC_API_KEY=...
SHOPEE_EMAIL=herlison14@gmail.com
SHOPEE_PASSWORD=...
TIKTOK_ACCESS_TOKEN=         # vazio — não configurado ainda
TIKTOK_REFRESH_TOKEN=
TIKTOK_OPEN_ID=
CAMPAIGN_NAME=campanha_2026
SOCIAL_NETWORK=tiktok
POST_TIMES=09:00,13:00,20:00
ANTHROPIC_MODEL=claude-opus-4-6
MAX_PRODUCTS_PER_RUN=100
HEADLESS=false
WHATSAPP_PHONE=5521997927927
```

## Problemas conhecidos e soluções
- **CAPTCHA no pipeline:** Sempre abrir Chrome via `start_chrome.bat` antes
- **0 produtos extraídos:** Shopee pode ter mudado o DOM — verificar scraper JS
- **CDP ECONNREFUSED:** Chrome não está aberto com `--remote-debugging-port=9222`
- **TargetClosedError screenshot:** Chrome fechado durante execução — ignorado silenciosamente
- **Token TikTok expirado:** Configurar `TIKTOK_ACCESS_TOKEN` no .env

## Arquivos de inicialização (Windows)
- `start_chrome.bat` — abre Chrome com CDP
- `iniciar_sistema.bat` — inicia dashboard Streamlit
- `agendar_tarefa.bat` — cria tarefa no Windows Task Scheduler (08:00)

## Deploy cloud
- `deploy_vps.sh` — instala em Oracle Cloud Free Tier (Ubuntu)
- `sync_session.bat` — envia sessão Shopee para VPS via SCP
- `.github/workflows/daily_pipeline.yml` — GitHub Actions (copy sem browser)
