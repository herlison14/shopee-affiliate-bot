# Shopee Affiliate Bot — Memória do Projeto

## Sobre o projeto
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
