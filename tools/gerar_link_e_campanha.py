"""
Ferramenta LOCAL (roda na sua maquina, nao no Render) que:
1. Usa o Chrome ja aberto e logado em affiliate.shopee.com.br (via CDP, igual o bot antigo)
   para gerar um link de afiliado real a partir da URL de um produto.
2. Chama a tool MCP `criar_campanha` do ShopeeViral.AI com o link gerado, criando a
   campanha (com legenda/hashtags por IA) direto no seu painel.

Pre-requisitos:
- Chrome aberto com `--remote-debugging-port=9222` e logado em affiliate.shopee.com.br
  (use o start_chrome.bat do projeto antigo, ou abra manualmente)
- pip install playwright httpx
- playwright install chromium  (so na primeira vez)
- Variavel de ambiente SHOPEEVIRAL_MCP_URL com a sua URL pessoal de MCP
  (pegue em /api/v1/auth/mcp-url logado no painel, ou na secao "Conectar com IA")

Uso:
    set SHOPEEVIRAL_MCP_URL=https://shopee-viral-api.onrender.com/agent/SEU_TOKEN/mcp
    python tools/gerar_link_e_campanha.py "Nome do produto" "https://shopee.com.br/produto-x"
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from automation.stealth import aplicar_stealth  # noqa: E402

AFFILIATE_URL = "https://affiliate.shopee.com.br"


async def gerar_link_afiliado(product_url: str) -> str | None:
    """Conecta no Chrome local via CDP e usa a ferramenta Custom Link da Shopee
    para gerar um link de afiliado rastreavel para o produto."""
    playwright = await async_playwright().start()
    try:
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
    except Exception as exc:
        await playwright.stop()
        raise RuntimeError(
            "Nao foi possivel conectar ao Chrome via CDP (porta 9222). "
            "Abra o Chrome com --remote-debugging-port=9222 e faca login em "
            "affiliate.shopee.com.br antes de rodar este script."
        ) from exc

    context = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = None
    for p in context.pages:
        if "affiliate.shopee.com.br" in p.url:
            page = p
            break
    if not page:
        page = context.pages[0] if context.pages else await context.new_page()

    await aplicar_stealth(context, page)

    try:
        await page.goto(f"{AFFILIATE_URL}/offer/custom_link", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        await page.evaluate(
            """
            (url) => {
                const textarea = document.querySelector('textarea');
                if (!textarea) return { ok: false };
                const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                setter.call(textarea, url);
                textarea.dispatchEvent(new Event('input', { bubbles: true }));
                textarea.dispatchEvent(new Event('change', { bubbles: true }));
                return { ok: true };
            }
            """,
            product_url,
        )
        await page.wait_for_timeout(1000)

        clicked = await page.evaluate(
            """
            () => {
                const btns = Array.from(document.querySelectorAll('button'))
                    .filter(b => /obter\\s*link/i.test(b.textContent) && !b.disabled);
                if (btns.length > 0) { btns[0].click(); return true; }
                return false;
            }
            """
        )
        if not clicked:
            raise RuntimeError("Botao 'Obter link' nao encontrado na pagina custom_link.")

        await page.wait_for_timeout(2500)

        link = await page.evaluate(
            """
            () => {
                const readonly = document.querySelector('input[readonly]');
                if (readonly && readonly.value && readonly.value.startsWith('http')) return readonly.value;
                const inputs = Array.from(document.querySelectorAll('input'));
                for (const inp of inputs) {
                    if (inp.value && inp.value.includes('s.shopee')) return inp.value;
                }
                const match = document.body.innerText.match(/(https?:\\/\\/s\\.shopee\\.com\\.br\\/[\\w\\-]+)/);
                return match ? match[1] : null;
            }
            """
        )
        return link
    finally:
        # CDP mode: nao fecha o browser do usuario, so a conexao.
        await browser.close()
        await playwright.stop()


def _parse_sse_json(text: str) -> dict:
    """Extrai o ultimo objeto JSON de uma resposta text/event-stream (formato 'data: {...}')."""
    last_data = None
    for line in text.splitlines():
        if line.startswith("data:"):
            last_data = line[len("data:"):].strip()
    if not last_data:
        raise RuntimeError(f"Resposta MCP sem 'data:' reconhecivel: {text!r}")
    return json.loads(last_data)


def chamar_mcp_tool(mcp_url: str, tool_name: str, arguments: dict) -> dict:
    """Cliente MCP minimo: faz o handshake initialize e chama uma tool, via HTTP puro."""
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}

    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "gerar_link_e_campanha.py", "version": "1.0"},
        },
    }
    resp = httpx.post(mcp_url, json=init_payload, headers=headers, timeout=30)
    resp.raise_for_status()

    call_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    resp = httpx.post(mcp_url, json=call_payload, headers=headers, timeout=30)
    resp.raise_for_status()
    result = _parse_sse_json(resp.text)

    if "error" in result:
        raise RuntimeError(f"Erro MCP: {result['error']}")
    return result["result"]


async def main() -> None:
    if len(sys.argv) < 3:
        print('Uso: python tools/gerar_link_e_campanha.py "Nome do produto" "https://shopee.com.br/produto-x"')
        sys.exit(1)

    nome_produto, url_produto = sys.argv[1], sys.argv[2]

    mcp_url = os.environ.get("SHOPEEVIRAL_MCP_URL")
    if not mcp_url:
        print("Defina a variavel de ambiente SHOPEEVIRAL_MCP_URL com sua URL pessoal de MCP.")
        sys.exit(1)

    print(f"Gerando link de afiliado para: {nome_produto}...")
    link_afiliado = await gerar_link_afiliado(url_produto)
    if not link_afiliado:
        print("Nao foi possivel gerar o link de afiliado. Veja os erros acima.")
        sys.exit(1)
    print(f"Link gerado: {link_afiliado}")

    print("Criando campanha no ShopeeViral.AI...")
    result = chamar_mcp_tool(
        mcp_url,
        "criar_campanha",
        {"nome_produto": nome_produto, "url_produto": url_produto, "link_afiliado": link_afiliado},
    )
    texto = result["content"][0]["text"]
    print("Campanha criada:")
    print(texto)


if __name__ == "__main__":
    asyncio.run(main())
