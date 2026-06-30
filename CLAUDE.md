# Shopee Affiliate Bot — Memória do Projeto

> Este repositório tem dois projetos distintos:
> 1. **ShopeeViral.AI** (`backend/` + `frontend/`) — SaaS novo, ver seção abaixo.
> 2. **Shopee Affiliate Bot** (raiz: `main.py`, `scraper/`, `dashboard/` etc.) — bot de scraping antigo, documentado no restante deste arquivo.

## ShopeeViral.AI (backend/ + frontend/)

SaaS para afiliados Shopee: gera campanhas com legenda/hashtags via IA (Claude), rastreia comissões, expõe um servidor MCP por usuário (Claude Desktop, ChatGPT) e tem uma vitrine pública por usuário.

- **Stack**: FastAPI + SQLAlchemy async + Alembic + PostgreSQL (`backend/`); React + Vite + Tailwind (`frontend/`)
- **Deploy**: Render (`backend/`, autoDeploy no push pra `main`) + Vercel (`frontend/`)
- **Agente autônomo "James"**: roda em background via APScheduler, promove rascunhos esquecidos, renova legendas sem venda, sugere replicar campanhas de sucesso — cada usuário liga/desliga em `agent_enabled`
- **Vitrine pública**: `/vitrine/:userId` no frontend, alimentada por `GET /api/v1/public/storefront/{user_id}` — só mostra campanhas com `affiliate_link` preenchido e status `posted`/`scheduled`. Editável em "Sua vitrine pública" no dashboard
- **Editar campanha**: `PATCH /api/v1/campaigns/{id}` (parcial, `exclude_unset`) edita `affiliate_link`/`caption`/`hashtags`; tool MCP `definir_link_afiliado`. No frontend, `components/CampaignCard.jsx` mostra cada campanha com fluxo manual de link: botão "Gerar link" (abre `affiliate.shopee.com.br/offer/custom_link` em nova aba) + "Copiar URL do produto" + campo pra colar o link gerado. Fluxo 100% manual, sem automação (ver decisão sobre Shopee abaixo)
- **Antes de comitar**: seguir o checklist em [CONTRIBUTING.md](./CONTRIBUTING.md) — testes do backend, build do frontend, validação pós-deploy

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
