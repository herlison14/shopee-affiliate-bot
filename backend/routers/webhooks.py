from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.campaign import Campaign
from models.commission import Commission
from schemas import CommissionWebhook
from services.payment_service import calculate_commission_split
from services.shopee_service import verify_push_signature

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/shopee/sale", status_code=201)
async def shopee_sale_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Recebe notificações de vendas rastreadas via link de afiliado e registra a comissão.

    Valida a assinatura HMAC do header Authorization e e idempotente por order_id:
    reenvios da mesma venda (comum em webhooks) nao duplicam a comissao.
    """
    raw_body = await request.body()
    signature = request.headers.get("Authorization")

    if not verify_push_signature(str(request.url), raw_body, signature):
        raise HTTPException(status_code=401, detail="Assinatura invalida")

    try:
        payload = CommissionWebhook.model_validate_json(raw_body)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    result = await db.execute(select(Campaign).where(Campaign.id == payload.campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    existing = await db.execute(select(Commission).where(Commission.order_id == payload.order_id))
    existing_commission = existing.scalar_one_or_none()
    if existing_commission:
        return {"commission_id": existing_commission.id, "status": existing_commission.status, "duplicate": True}

    split = calculate_commission_split(payload.sale_amount)
    commission = Commission(
        campaign_id=campaign.id,
        order_id=payload.order_id,
        sale_amount=split["sale_amount"],
        commission_amount=split["net_commission"],
        platform_fee=split["platform_fee"],
        status="pending",
    )
    db.add(commission)

    try:
        await db.commit()
    except IntegrityError:
        # Corrida entre dois envios simultaneos da mesma venda.
        await db.rollback()
        existing = await db.execute(select(Commission).where(Commission.order_id == payload.order_id))
        existing_commission = existing.scalar_one()
        return {"commission_id": existing_commission.id, "status": existing_commission.status, "duplicate": True}

    await db.refresh(commission)
    return {"commission_id": commission.id, "status": commission.status}
