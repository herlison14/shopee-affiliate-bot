---
description: Posta automaticamente no Shopee Videos os produtos prontos na fila
---

# Auto Post Shopee

Você é um agente de automação do Shopee Affiliate Bot. Sua tarefa é:

1. Ler o arquivo `data/output.xlsx` e encontrar produtos com `status_agendamento == "pendente"`
2. Para cada produto pendente (máx 5 por execução):
   a. Verificar se existe vídeo em `data/videos/` para esse produto
   b. Se existir vídeo: postar no Shopee via browser automation (shopee_video_poster.py)
   c. Se não existir vídeo: registrar na fila manual (manual_queue.json)
3. Após postar: atualizar status no Excel para "publicado_shopee"
4. Enviar notificação WhatsApp confirmando postagem

## Como executar

```bash
cd C:\Users\herli\Downloads\shopee-affiliate-bot
python -c "
from scheduler.post_scheduler import dispatch_post_job
from config.settings import settings
import threading
lock = threading.Lock()
dispatch_post_job(settings, lock)
print('Job executado!')
"
```

## Verificação de sucesso

- Excel atualizado com status "publicado_shopee" ou "fila_manual"
- Log em logs/affiliate_bot.log mostra "✅ Shopee Video publicado"
- Screenshot salvo em logs/screenshots/ se erro ocorrer

## Arquivos relevantes

- `scheduler/post_scheduler.py` — dispatch_post_job()
- `scheduler/shopee_video_poster.py` — automação Playwright
- `scheduler/video_downloader.py` — download automático de vídeos
- `data/videos/` — pasta com vídeos para postagem
- `data/output.xlsx` — produtos e status
- `data/manual_queue.json` — fila manual quando sem vídeo
