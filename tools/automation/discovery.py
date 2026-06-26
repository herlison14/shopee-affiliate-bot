"""Descoberta e ranking de produtos, reaproveitando o scraper do bot antigo.

Nota: o arquivo antigo scraper/product_ranker.py usa campos como 'rating' e
'vendas' que NUNCA sao de fato extraidos pelo scraper (confirmado lendo
scraper/shopee_affiliate.py -- os unicos campos reais sao 'produto',
'comissao_novo' e 'preco'; 'comissao_atual' e uma estimativa fabricada,
nao um dado real). Por isso este modulo reimplementa o ranking usando
so os campos que sao de fato confiaveis, em vez de importar o ranker antigo.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


async def descobrir_produtos(max_produtos: int = 20, min_comissao_pct: float = 8.0) -> list[dict]:
    """Usa o Chrome local (CDP) ja logado no portal de afiliados para
    descobrir produtos com link de afiliado gerado."""
    from config.settings import get_settings
    from scraper.shopee_affiliate import scrape_all_products

    settings = get_settings()
    produtos = await scrape_all_products(settings)
    return [p for p in produtos if p.get("comissao_novo", 0) >= min_comissao_pct][:max_produtos]


def rankear_produtos(produtos: list[dict], top_n: int = 5) -> list[dict]:
    """Ordena por comissao real (comissao_novo) e preco, removendo duplicados
    pelo product_id. So usa campos confirmadamente reais -- nao usa
    'comissao_atual' (fabricada) nem 'rating'/'vendas' (nunca extraidos)."""
    vistos = set()
    unicos = []
    for p in produtos:
        pid = p.get("product_id") or p.get("link_original")
        if pid in vistos:
            continue
        vistos.add(pid)
        unicos.append(p)

    unicos.sort(key=lambda p: (p.get("comissao_novo", 0), p.get("preco", 0)), reverse=True)
    return unicos[:top_n]
