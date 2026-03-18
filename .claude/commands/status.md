Faça um diagnóstico completo do sistema Shopee Affiliate Bot verificando:

1. **Chrome CDP** — testa se está ativo na porta 9222 com `curl -s http://localhost:9222/json`
2. **Dashboard** — testa se está rodando em http://localhost:8501
3. **API Anthropic** — carrega o .env e testa uma chamada real com o modelo configurado
4. **Últimos logs** — lê as últimas 30 linhas de `logs/affiliate_bot.log` e resume erros/sucessos
5. **Excel** — verifica quantos produtos existem em `data/output.xlsx` e o status de cada um
6. **Créditos API** — indica se a API respondeu com sucesso ou erro de saldo

Apresente o resultado em formato de tabela com ✅ / ❌ / ⚠️ para cada item, seguido de um resumo do que precisa ser feito.
