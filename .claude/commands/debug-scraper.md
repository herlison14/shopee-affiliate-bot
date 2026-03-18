Analise falhas no scraper do Shopee Affiliate Bot:

1. Leia o arquivo completo `logs/affiliate_bot.log`
2. Identifique e categorize todos os erros encontrados:
   - CAPTCHA detectado
   - 0 produtos coletados
   - Timeout / elemento não encontrado
   - CDP desconectado
   - Erro de login / sessão expirada
3. Leia o arquivo `scraper/shopee_affiliate.py` e verifique se os seletores CSS/JS ainda fazem sentido
4. Verifique o arquivo `data/.shopee_session.json` — existe? está recente?
5. Apresente:
   - Causa raiz mais provável do problema
   - Solução passo a passo
   - Se necessário, sugira ajustes no código do scraper
