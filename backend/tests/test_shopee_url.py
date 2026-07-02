import pytest

from services.shopee_url import (
    extract_ids,
    is_stable_product_url,
    normalize_product_url,
)

CANONICAL = "https://shopee.com.br/product/123456/789012"


def test_extract_ids_do_formato_slug():
    url = "https://shopee.com.br/Beauty-of-Joseon-Serum-i.123456.789012"
    assert extract_ids(url) == ("123456", "789012")


def test_extract_ids_do_formato_product_path():
    assert extract_ids(CANONICAL) == ("123456", "789012")


def test_extract_ids_ignora_link_de_oferta():
    # Link de oferta temporario nao embute shop_id/item_id.
    assert extract_ids("https://shopee.com.br/offer/product_offer/23798128210") is None


def test_extract_ids_ignora_link_encurtado():
    assert extract_ids("https://s.shopee.com.br/abc123XYZ") is None


@pytest.mark.parametrize(
    "url,estavel",
    [
        ("https://shopee.com.br/Produto-i.111.222", True),
        ("https://shopee.com.br/product/111/222", True),
        ("https://shopee.com.br/offer/product_offer/23798128210", False),
        ("https://s.shopee.com.br/abc123", False),
        ("", False),
    ],
)
def test_is_stable_product_url(url, estavel):
    assert is_stable_product_url(url) is estavel


def test_normalize_slug_vira_forma_canonica():
    url = "https://shopee.com.br/Beauty-of-Joseon-i.123456.789012?sp_atk=abc&xptdk=xyz"
    assert normalize_product_url(url) == CANONICAL


def test_normalize_link_de_oferta_fica_inalterado():
    # Sem IDs pra extrair, devolve a URL original (o chamador sinaliza como instavel).
    oferta = "https://shopee.com.br/offer/product_offer/23798128210"
    assert normalize_product_url(oferta) == oferta


def test_duas_urls_do_mesmo_produto_normalizam_igual():
    slug = "https://shopee.com.br/Nome-Diferente-i.123456.789012"
    path = "https://shopee.com.br/product/123456/789012?utm=x"
    assert normalize_product_url(slug) == normalize_product_url(path) == CANONICAL
