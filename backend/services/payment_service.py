import stripe

from config import settings

stripe.api_key = settings.STRIPE_API_KEY


def create_checkout_session(user_email: str, success_url: str, cancel_url: str) -> dict:
    """Stub: cria sessão de checkout Stripe para o plano Pro. PIX via Asaas pode ser plugado aqui."""
    if not settings.STRIPE_API_KEY:
        return {"id": "stub_session", "url": success_url}

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=user_email,
        line_items=[{"price_data": {
            "currency": "brl",
            "product_data": {"name": "ShopeeViral.AI Pro"},
            "recurring": {"interval": "month"},
            "unit_amount": 5000,
        }, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return {"id": session.id, "url": session.url}


def calculate_commission_split(sale_amount: float) -> dict:
    platform_fee = round(sale_amount * settings.COMMISSION_RATE, 2)
    net_commission = round(sale_amount - platform_fee, 2)
    return {"sale_amount": sale_amount, "platform_fee": platform_fee, "net_commission": net_commission}
