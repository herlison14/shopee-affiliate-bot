from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.campaign import Campaign
from models.user import User
from schemas import CampaignOut, InstagramConnect, InstagramStatusOut
from security import get_current_user
from services import instagram_service
from services.instagram_service import InstagramError

router = APIRouter(prefix="/api/v1/instagram", tags=["instagram"])


@router.post("/connect", response_model=InstagramStatusOut)
async def connect_instagram(
    payload: InstagramConnect,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Conecta a conta Instagram do usuario. O token de longa duracao e obtido por
    ele no Meta for Developers (OAuth) -- aqui a gente valida e guarda."""
    # valida o token buscando a conta antes de salvar
    current_user.instagram_access_token = payload.access_token
    current_user.instagram_user_id = payload.instagram_user_id
    try:
        info = await instagram_service.get_account_info(current_user)
    except InstagramError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    await db.commit()
    return InstagramStatusOut(connected=True, username=info.get("username"))


@router.get("/status", response_model=InstagramStatusOut)
async def instagram_status(current_user: User = Depends(get_current_user)):
    if not current_user.instagram_access_token:
        return InstagramStatusOut(connected=False, detail="Nenhuma conta Instagram conectada.")
    try:
        info = await instagram_service.get_account_info(current_user)
        return InstagramStatusOut(connected=True, username=info.get("username"))
    except InstagramError as exc:
        return InstagramStatusOut(connected=False, detail=str(exc))


@router.post("/campaigns/{campaign_id}/publish", response_model=CampaignOut)
async def publish_campaign(
    campaign_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Publica a campanha no feed do Instagram (foto + legenda). Exige conta
    conectada e image_url na campanha."""
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    if not current_user.instagram_access_token:
        raise HTTPException(status_code=400, detail="Conta Instagram não conectada.")
    if not campaign.image_url:
        raise HTTPException(status_code=400, detail="Campanha sem imagem. Adicione uma image_url.")

    caption = instagram_service.build_caption(campaign.caption, campaign.hashtags)
    try:
        result_pub = await instagram_service.publish_photo(current_user, campaign.image_url, caption)
    except InstagramError as exc:
        campaign.status = "needs_review"
        campaign.status_detail = f"Falha ao publicar no Instagram: {exc}"
        await db.commit()
        raise HTTPException(status_code=502, detail=str(exc))

    campaign.status = "posted"
    campaign.posted_url = result_pub["posted_url"]
    campaign.status_detail = None
    await db.commit()
    await db.refresh(campaign)
    return campaign
