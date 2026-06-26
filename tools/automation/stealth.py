"""Mascara sinais de automacao ao conectar via CDP a um Chrome ja aberto.

Achado em 2026-06-26: o Chrome expoe navigator.webdriver=true assim que QUALQUER
cliente CDP se conecta a uma aba, independente de flags de lancamento ou do
perfil usado. Confirmado empiricamente: navegacao manual na mesma sessao
funciona normalmente; navegacao via Playwright (mesma sessao, mesmo perfil)
e redirecionada para tela de login pela Shopee a cada page.goto(). Sem esse
patch, qualquer automacao via connect_over_cdp tende a ser detectada.
"""

STEALTH_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
    window.chrome = window.chrome || { runtime: {} };
"""


async def aplicar_stealth(context, page) -> None:
    """Aplica o patch tanto para navegacoes futuras (init script no context)
    quanto para a pagina ja carregada agora (evaluate direto)."""
    await context.add_init_script(STEALTH_SCRIPT)
    try:
        await page.evaluate(STEALTH_SCRIPT)
    except Exception:
        pass
