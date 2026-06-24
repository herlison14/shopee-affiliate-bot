from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.campaign import Campaign
from models.user import User
from schemas import CampaignCreate, CampaignOut
from security import get_current_user
from services.ai_service import generate_caption_and_hashtags

router = APIRouter(prefix="/api/v1/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Campaign).where(Campaign.user_id == current_user.id).order_by(Campaign.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=CampaignOut, status_code=201)
async def create_campaign(
    payload: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    caption, hashtags = await generate_caption_and_hashtags(payload.product_name)

    campaign = Campaign(
        user_id=current_user.id,
        product_name=payload.product_name,
        product_url=payload.product_url,
        affiliate_link=payload.affiliate_link,
        caption=caption,
        hashtags=hashtags,
        status="scheduled" if payload.scheduled_for else "draft",
        scheduled_for=payload.scheduled_for,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(
    campaign_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    return campaign


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(
    campaign_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    await db.delete(campaign)
    await db.commit()
