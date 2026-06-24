from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.campaign import Campaign
from models.commission import Commission
from schemas import CommissionWebhook
from services.payment_service import calculate_commission_split

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/shopee/sale", status_code=201)
async def shopee_sale_webhook(payload: CommissionWebhook, db: AsyncSession = Depends(get_db)):
    """Recebe notificações de vendas rastreadas via link de afiliado e registra a comissão."""
    result = await db.execute(select(Campaign).where(Campaign.id == payload.campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

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
    await db.commit()
    await db.refresh(commission)
    return {"commission_id": commission.id, "status": commission.status}
