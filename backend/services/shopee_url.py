"""Normalizacao e validacao de URLs de produto da Shopee.

Problema que isto resolve: links de oferta temporarios
(`shopee.com.br/offer/product_offer/{id}`) e encurtados (`s.shopee.com.br/...`)
sao dinamicos e expiram -- nao fixam um produto especifico. Uma campanha criada
com esse tipo de URL nasce quebrada: o link de afiliado gerado em cima dela para
de funcionar quando a oferta expira.

A URL canonica e estavel do produto embute `shop_id` e `item_id`, em dois formatos:
    https://shopee.com.br/Nome-do-Produto-i.{shop_id}.{item_id}
    https://shopee.com.br/product/{shop_id}/{item_id}

Aqui a gente extrai esses IDs, normaliza pra forma canonica `/product/{shop}/{item}`
e sinaliza quando a URL nao fixa um produto estavel.
"""

import re

# IDs do produto: "-i.{shop_id}.{item_id}" (slug) ou "/product/{shop_id}/{item_id}" (path).
_ID_SLUG = re.compile(r"-i\.(\d+)\.(\d+)")
_ID_PATH = re.compile(r"/product/(\d+)/(\d+)")

UNSTABLE_URL_WARNING = (
    "⚠️ URL instável: parece um link de oferta/temporário (ex.: /offer/... ou "
    "encurtado s.shopee.com.br), que expira. Substitua pela URL do produto no "
    "formato shopee.com.br/...-i.LOJA.ITEM ou /product/LOJA/ITEM para gerar um "
    "link de afiliado que não quebra."
)


def extract_ids(url: str) -> tuple[str, str] | None:
    """Retorna (shop_id, item_id) se a URL embutir a identificacao do produto; senao None."""
    if not url:
        return None
    match = _ID_SLUG.search(url) or _ID_PATH.search(url)
    if match:
        return match.group(1), match.group(2)
    return None


def is_stable_product_url(url: str) -> bool:
    """True se a URL fixa um produto de forma estavel (tem shop_id + item_id embutidos).

    Links de oferta (/offer/product_offer/...) e encurtados (s.shopee.com.br) nao
    tem esses IDs e retornam False -- link de afiliado gerado sobre eles expira.
    """
    return extract_ids(url) is not None


def normalize_product_url(url: str) -> str:
    """Devolve a URL canonica estavel (`shopee.com.br/product/{shop}/{item}`) quando da
    pra extrair os IDs; senao devolve a URL original inalterada (o chamador decide se
    sinaliza como instavel via `is_stable_product_url`). Nao levanta erro."""
    ids = extract_ids(url)
    if not ids:
        return url
    shop_id, item_id = ids
    return f"https://shopee.com.br/product/{shop_id}/{item_id}"
