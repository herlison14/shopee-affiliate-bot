import re
import unicodedata
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse, urljoin


def clean_product_name_for_subid(name: str) -> str:
    """Normalize product name for use as a Shopee SubID (max 50 chars)."""
    # Remove accents
    normalized = unicodedata.normalize("NFKD", name)
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
    # Lowercase, replace spaces with underscores
    cleaned = ascii_str.lower().replace(" ", "_")
    # Remove anything that's not alphanumeric or underscore
    cleaned = re.sub(r"[^a-z0-9_]", "", cleaned)
    # Collapse multiple underscores
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:50]


def build_subids(product_name: str, social_network: str, campaign: str) -> dict:
    """Build the SubID dict for Shopee affiliate link tracking."""
    return {
        "nome_do_produto": clean_product_name_for_subid(product_name),
        "rede_social": social_network[:50],
        "campanha_atual": campaign[:50],
    }


def inject_subids_into_url(affiliate_url: str, subids: dict) -> str:
    """Append SubID query parameters to an existing affiliate URL."""
    parsed = urlparse(affiliate_url)
    existing_params = parse_qs(parsed.query, keep_blank_values=True)

    # Merge SubIDs (SubIDs override existing same-named params)
    for key, value in subids.items():
        existing_params[key] = [value]

    # Rebuild query string (flat values, not lists)
    flat_params = {k: v[0] for k, v in existing_params.items()}
    new_query = urlencode(flat_params)

    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)


def validate_affiliate_url(url: str) -> bool:
    """Basic sanity check that a URL looks like a Shopee affiliate link."""
    if not url:
        return False
    parsed = urlparse(url)
    shopee_domains = ("shopee.com.br", "s.shopee.com.br", "shp.ee")
    return any(d in parsed.netloc for d in shopee_domains)
