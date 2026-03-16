"""
Claude API integration for generating viral affiliate marketing copy.
Outputs JSON: overlay, legenda, hashtags, estrategia_curta.
"""

import json
import logging
import re
import time

import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é um Growth Hacker e Copywriter Sênior especializado em marketing de afiliados para o público brasileiro.
Seu objetivo é criar conteúdo viral para TikTok e Shopee Vídeos que converta em vendas.

DIRETRIZES:
- Português brasileiro coloquial, entusiasta e direto
- Tom de "criador de conteúdo real", não de propaganda corporativa
- Use gatilhos mentais: escassez, curiosidade, prova social
- Use frases como "Eu não sabia que precisava disso até...", "O preço disso é bizarro", "Finalmente chegou no Brasil"
- O overlay deve ter no máximo 5 palavras IMPACTANTES para aparecer na tela do vídeo
- A legenda deve incluir o link afiliado fornecido e emojis estratégicos
- CTA claro: orientar o usuário a clicar no link da bio ou ícone de carrinho
- OBRIGATÓRIO ao final da legenda: "\\n\\n🤖 Conteúdo com apoio de IA | #publi"
- Hashtags específicas para o nicho do produto + gerais de e-commerce BR

FORMATO DE RESPOSTA — retorne APENAS um objeto JSON válido, sem markdown:
{
  "overlay": "Frase curta 3-5 palavras",
  "legenda": "Texto completo com emojis, CTA e link afiliado",
  "hashtags": "#hashtag1 #hashtag2 #shopeebr",
  "estrategia_curta": "1 frase explicando por que esse post vai viralizar"
}"""

USER_PROMPT_TEMPLATE = """Produto: {product_name}
Categoria: {category}
Comissão novos compradores: {commission_new}%
Comissão compradores existentes: {commission_existing}%
Link afiliado: {affiliate_link}
Rede social alvo: {social_network}

Crie o conteúdo de marketing viral para este produto."""

REQUIRED_KEYS = {"overlay", "legenda", "hashtags", "estrategia_curta"}

FALLBACK_COPY = {
    "overlay": "Achou incrível aqui 🔥",
    "legenda": (
        "Olha esse produto incrível que encontrei! 😍\n"
        "Preço absurdo e qualidade top!\n\n"
        "🛒 Corre no link da bio!\n\n"
        "🤖 Conteúdo com apoio de IA | #publi"
    ),
    "hashtags": "#shopee #achadinhos #shopeebr #compraonline #promoção",
    "estrategia_curta": "Conteúdo genérico de fallback — geração de IA falhou.",
    "ai_status": "ai_failed",
}


def parse_ai_response(raw_text: str) -> dict:
    """Strip markdown fences and parse JSON from Claude's response."""
    # Remove ```json ... ``` or ``` ... ``` fences
    cleaned = re.sub(r"```(?:json)?\s*", "", raw_text).replace("```", "").strip()
    data = json.loads(cleaned)
    missing = REQUIRED_KEYS - set(data.keys())
    if missing:
        raise ValueError(f"Chaves faltando na resposta: {missing}")
    return data


def generate_copy(product: dict, client: anthropic.Anthropic, model: str) -> dict:
    """
    Call Claude API to generate viral copy for a single product.
    Retries once on JSON parse failure.
    """
    user_prompt = USER_PROMPT_TEMPLATE.format(
        product_name=product.get("produto", "Produto"),
        category=product.get("category", "Geral"),
        commission_new=product.get("comissao_novo", 0),
        commission_existing=product.get("comissao_atual", 0),
        affiliate_link=product.get("link_afiliado", product.get("link_original", "")),
        social_network=product.get("social_network", "tiktok"),
    )

    for attempt in range(2):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=800,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw = response.content[0].text
            copy_data = parse_ai_response(raw)
            copy_data["ai_status"] = "success"
            return {**product, **copy_data}

        except json.JSONDecodeError as e:
            logger.warning(f"JSON inválido na tentativa {attempt + 1}: {e}")
            if attempt == 0:
                # Retry with explicit instruction
                user_prompt += "\n\nIMPORTANTE: Retorne APENAS o JSON, sem texto adicional."
                time.sleep(1)
                continue
            break
        except Exception as e:
            logger.error(f"Erro na API Claude para '{product.get('produto')}': {e}")
            break

    # Return fallback copy merged with product data
    fallback = {**product, **FALLBACK_COPY}
    fallback["legenda"] = (
        fallback["legenda"].replace(
            "🛒 Corre no link da bio!",
            f"🛒 Link: {product.get('link_afiliado', '')}\nCorre no link da bio!",
        )
    )
    return fallback


def generate_batch(products: list, api_key: str, model: str) -> list:
    """Generate copy for all products. Returns enriched list."""
    client = anthropic.Anthropic(api_key=api_key)
    results = []
    total = len(products)

    for i, product in enumerate(products):
        logger.info(f"[{i+1}/{total}] Gerando copy: {product.get('produto', '')[:50]}")
        enriched = generate_copy(product, client, model)
        results.append(enriched)
        # Respect API rate limits
        if i < total - 1:
            time.sleep(0.5)

    success = sum(1 for r in results if r.get("ai_status") == "success")
    logger.info(f"Copy gerado: {success}/{total} com sucesso.")
    return results
