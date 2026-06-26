# tools/ — ferramentas locais (não fazem parte do deploy)

Scripts que rodam na sua máquina, não no Render. Não são deployados; usam o Chrome local com sessão logada (mesmo padrão do bot antigo).

## gerar_link_e_campanha.py

Gera um link de afiliado real na Shopee (via automação do Chrome local, reaproveitando a
sessão logada em affiliate.shopee.com.br) e cria a campanha correspondente no ShopeeViral.AI,
chamando direto a tool MCP `criar_campanha` do seu painel.

### Por que existe

A API oficial da Shopee (Open Platform) é para vendedores/parceiros de software, não para
afiliados — não dá pra automatizar isso via API. A única forma de gerar o link é pela
interface web do portal de afiliados, por isso a automação de navegador.

### Setup (uma vez)

```bash
pip install playwright httpx
playwright install chromium
```

Abra o Chrome com debugging remoto e faça login no portal de afiliados (pode reaproveitar o
`start_chrome.bat` do projeto antigo, na raiz do repo):

```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\ChromeDebug
```

Depois logue manualmente em https://affiliate.shopee.com.br nessa janela.

### Uso

Pegue sua URL pessoal de MCP no painel (seção "Conectar com IA") ou via
`GET /api/v1/auth/mcp-url`, e defina:

```powershell
$env:SHOPEEVIRAL_MCP_URL = "https://shopee-viral-api.onrender.com/agent/SEU_TOKEN/mcp"
python tools/gerar_link_e_campanha.py "Nome do produto" "https://shopee.com.br/produto-x"
```

O script abre a aba do Custom Link no Chrome já aberto, gera o link rastreável, e cria a
campanha (com legenda/hashtags geradas por IA) no seu painel — sem você precisar colar nada
manualmente.

### Limitação conhecida

Continua sem solução: **rastrear se a venda de fato aconteceu**. A Shopee não expõe isso via
API nem via scraping confiável (o bot antigo nunca fez isso de verdade — só estimava). Esse
script resolve só a geração do link, não a confirmação de comissão.
