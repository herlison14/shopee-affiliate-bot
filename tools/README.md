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

## automation/ — pipeline completo automatizado

Pacote que une descoberta de produtos + geração de link + criação de campanha com IA + busca
de vídeo relevante + (opcional) postagem automática no Shopee Videos — tudo em um só
orquestrador, rodando local.

### Por que existe

O bot antigo já tinha cada uma dessas partes separadas, mas com gambiarras sérias:
baixava o primeiro vídeo do YouTube sem checar relação com o produto, e **fingia sucesso**
ao postar quando não conseguia confirmar (`status: success, note: posted_unconfirmed`).
Isso é tolerável com supervisão humana, mas perigoso num pipeline 100% automático — por
isso esse pacote reimplementa essas duas partes com checagem real antes de automatizar tudo.

### O que cada módulo faz

- `discovery.py` — reaproveita `scraper/shopee_affiliate.py` do bot antigo (Chrome CDP) para
  descobrir produtos com link de afiliado já gerado. Ranking usa só campos confirmadamente
  reais (`comissao_novo`, `preco`) — o ranker antigo usava `rating`/`vendas`, que nunca são
  de fato extraídos pelo scraper.
- `video_match.py` — busca até 5 candidatos de vídeo no YouTube (metadata, sem baixar nada
  ainda), pontua a relevância de cada um pelo título vs. nome do produto, e **só baixa se
  algum candidato passar do limiar mínimo**. Sem vídeo relevante, a campanha fica marcada
  `needs_review` em vez de postar algo sem relação com o produto.
- `shopee_poster.py` — posta o vídeo no Shopee Videos via Chrome local. Só retorna sucesso
  se houver confirmação real (mudança de URL ou elemento de sucesso na página) — nunca
  finge sucesso.
- `orchestrator.py` — liga tudo: descobre → gera link → cria campanha (MCP) → busca vídeo
  relevante → posta (se `--auto-postar`) → atualiza status real da campanha no painel.

### Setup (além do já descrito acima)

```bash
pip install -U yt-dlp
```

(`yt-dlp` é usado para buscar metadata de vídeos e baixar o escolhido.)

### Uso

```powershell
$env:SHOPEEVIRAL_MCP_URL = "https://shopee-viral-api.onrender.com/agent/SEU_TOKEN/mcp"

# Modo seguro (recomendado para os primeiros testes): prepara tudo, mas NAO posta sozinho
python tools/automation/orchestrator.py --uma-vez

# Modo totalmente automatico: posta de fato no Shopee Videos
python tools/automation/orchestrator.py --uma-vez --auto-postar

# Loop continuo, rodando sozinho a cada 6h (Ctrl+C para parar)
python tools/automation/orchestrator.py --ciclo-horas 6 --auto-postar
```

Flags disponíveis: `--max-produtos` (quantos descobrir), `--min-comissao` (filtro mínimo),
`--top-n` (quantos processar por ciclo), `--auto-postar` (sem essa flag, o pipeline prepara
tudo — link, campanha, vídeo — mas deixa a postagem final para você fazer manualmente).

**Recomendação**: rode algumas vezes sem `--auto-postar` primeiro, confira no painel se as
campanhas e vídeos escolhidos fazem sentido, e só então ative a postagem automática.

### O que continua manual/sem solução

- **Confirmar se a venda aconteceu de verdade** — nenhuma automação resolve isso, é
  limitação da própria Shopee (ver seção acima).
- **Login inicial e CAPTCHA** — você precisa abrir o Chrome e logar manualmente de tempos
  em tempos, quando a sessão expirar.
