Execute o pipeline completo do Shopee Affiliate Bot e monitore até terminar:

1. Verifique se o Chrome CDP está ativo na porta 9222
2. Verifique se a API Anthropic está funcionando
3. Execute `python main.py` em background
4. Monitore o arquivo `logs/affiliate_bot.log` a cada 10 segundos até o pipeline terminar
5. Ao finalizar, apresente um resumo com:
   - Quantos produtos foram coletados
   - Quantos copies foram gerados com sucesso
   - Quantos falharam e por quê
   - Status final (sucesso / falha parcial / falha total)
   - Próximos passos recomendados
