from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.campaign import Campaign
from models.commission import Commission
from models.user import User
from schemas import (
    StorefrontCampaignOut,
    StorefrontOut,
    StorefrontSettingsOut,
    StorefrontSettingsUpdate,
)
from security import get_current_user

router = APIRouter(tags=["storefront"])


@router.get("/api/v1/storefront/settings", response_model=StorefrontSettingsOut)
async def get_storefront_settings(request: Request, current_user: User = Depends(get_current_user)):
    base_url = str(request.base_url).rstrip("/")
    return StorefrontSettingsOut(
        storefront_name=current_user.storefront_name or current_user.full_name or "Minha Vitrine",
        storefront_bio=current_user.storefront_bio,
        storefront_url=f"{base_url}/vitrine/{current_user.id}",
    )


@router.put("/api/v1/storefront/settings", response_model=StorefrontSettingsOut)
async def update_storefront_settings(
    payload: StorefrontSettingsUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.storefront_name = payload.storefront_name
    current_user.storefront_bio = payload.storefront_bio
    await db.commit()

    base_url = str(request.base_url).rstrip("/")
    return StorefrontSettingsOut(
        storefront_name=current_user.storefront_name,
        storefront_bio=current_user.storefront_bio,
        storefront_url=f"{base_url}/vitrine/{current_user.id}",
    )


@router.get("/api/v1/public/storefront/{user_id}", response_model=StorefrontOut)
async def get_public_storefront(user_id: str, db: AsyncSession = Depends(get_db)):
    """Vitrine publica: sem autenticacao, mostra so campanhas com link de afiliado
    preenchido e status 'posted' ou 'scheduled' -- nunca rascunhos ou links quebrados."""
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="Vitrine não encontrada")

    result = await db.execute(
        select(Campaign)
        .where(
            Campaign.user_id == user_id,
            Campaign.affiliate_link.is_not(None),
            Campaign.status.in_(["posted", "scheduled"]),
        )
        .order_by(Campaign.created_at.desc())
    )
    campaigns = result.scalars().all()

    campanhas_out = []
    for c in campaigns:
        has_sale = (
            await db.execute(select(Commission.id).where(Commission.campaign_id == c.id))
        ).scalar_one_or_none()
        campanhas_out.append(
            StorefrontCampaignOut(
                product_name=c.product_name,
                affiliate_link=c.affiliate_link,
                featured=has_sale is not None,
            )
        )

    return StorefrontOut(
        storefront_name=user.storefront_name or user.full_name or "Minha Vitrine",
        storefront_bio=user.storefront_bio,
        campaigns=campanhas_out,
    )
