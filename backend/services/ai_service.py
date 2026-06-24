from anthropic import AsyncAnthropic

from config import settings

_client: AsyncAnthropic | None = None


def get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


async def generate_caption_and_hashtags(product_name: str) -> tuple[str, str]:
    if not settings.ANTHROPIC_API_KEY:
        return (
            f"Confira essa novidade: {product_name}! Aproveite agora 🔥",
            "#shopee #achadinhos #promocao",
        )

    client = get_client()
    prompt = (
        f"Crie uma legenda curta e viral em português do Brasil para um vídeo de afiliado Shopee "
        f"do produto '{product_name}'. Depois, em uma segunda linha, liste 5 hashtags relevantes "
        f"separadas por espaço. Responda apenas com a legenda na primeira linha e as hashtags na segunda."
    )
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    lines = [l for l in text.split("\n") if l.strip()]
    caption = lines[0] if lines else f"Confira: {product_name}"
    hashtags = lines[1] if len(lines) > 1 else "#shopee #achadinhos"
    return caption, hashtags
