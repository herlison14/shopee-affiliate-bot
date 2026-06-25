from datetime import timedelta

from sqlalchemy import select

import database
from models.agent_action import AgentAction
from models.campaign import Campaign
from models.commission import Commission
from models.user import User
from services.ai_service import generate_caption_and_hashtags

DRAFT_PROMOTE_AFTER_HOURS = 24
UNDERPERFORMING_AFTER_DAYS = 7

AGENT_NAME = "James"


def _enabled_users_subquery():
    return select(User.id).where(User.agent_enabled.is_(True), User.is_active.is_(True))


async def _log_action(db, user_id: str, campaign_id: str | None, action_type: str, description: str) -> None:
    db.add(AgentAction(user_id=user_id, campaign_id=campaign_id, action_type=action_type, description=description))


async def _promote_stale_drafts(db) -> int:
    cutoff = database.utcnow() - timedelta(hours=DRAFT_PROMOTE_AFTER_HOURS)
    result = await db.execute(
        select(Campaign).where(
            Campaign.status == "draft",
            Campaign.created_at <= cutoff,
            Campaign.user_id.in_(_enabled_users_subquery()),
        )
    )
    promoted = 0
    for campaign in result.scalars().all():
        campaign.status = "scheduled"
        await _log_action(
            db,
            campaign.user_id,
            campaign.id,
            "promover_draft",
            f"Campanha '{campaign.product_name}' estava em rascunho ha mais de "
            f"{DRAFT_PROMOTE_AFTER_HOURS}h e foi promovida automaticamente para 'scheduled'.",
        )
        promoted += 1
    return promoted


async def _refresh_underperforming_campaigns(db) -> int:
    cutoff = database.utcnow() - timedelta(days=UNDERPERFORMING_AFTER_DAYS)
    result = await db.execute(
        select(Campaign).where(
            Campaign.status.in_(["scheduled", "posted"]),
            Campaign.created_at <= cutoff,
            Campaign.user_id.in_(_enabled_users_subquery()),
        )
    )
    refreshed = 0
    for campaign in result.scalars().all():
        has_sale = (
            await db.execute(select(Commission.id).where(Commission.campaign_id == campaign.id))
        ).scalar_one_or_none()
        if has_sale is not None:
            continue

        already_refreshed = (
            await db.execute(
                select(AgentAction.id).where(
                    AgentAction.campaign_id == campaign.id,
                    AgentAction.action_type == "regenerar_legenda",
                )
            )
        ).scalar_one_or_none()
        if already_refreshed is not None:
            continue

        caption, hashtags = await generate_caption_and_hashtags(campaign.product_name)
        campaign.caption = caption
        campaign.hashtags = hashtags
        await _log_action(
            db,
            campaign.user_id,
            campaign.id,
            "regenerar_legenda",
            f"Campanha '{campaign.product_name}' nao teve vendas em {UNDERPERFORMING_AFTER_DAYS} dias; "
            "legenda e hashtags foram regeneradas para tentar melhorar a performance.",
        )
        refreshed += 1
    return refreshed


async def _suggest_replicating_top_performers(db) -> int:
    """Campanhas que ja venderam sao bons candidatos a replicar para produtos parecidos."""
    result = await db.execute(
        select(Campaign.id, Campaign.user_id, Campaign.product_name)
        .join(Commission, Commission.campaign_id == Campaign.id)
        .where(Campaign.user_id.in_(_enabled_users_subquery()))
        .distinct()
    )
    suggested = 0
    for campaign_id, user_id, product_name in result.all():
        already_suggested = (
            await db.execute(
                select(AgentAction.id).where(
                    AgentAction.campaign_id == campaign_id,
                    AgentAction.action_type == "sugerir_replicar",
                )
            )
        ).scalar_one_or_none()
        if already_suggested is not None:
            continue

        await _log_action(
            db,
            user_id,
            campaign_id,
            "sugerir_replicar",
            f"A campanha '{product_name}' converteu pelo menos uma venda. Vale criar campanhas "
            "para produtos parecidos enquanto o interesse esta alto.",
        )
        suggested += 1
    return suggested


async def run_agent_cycle() -> dict:
    """Ciclo autonomo do agente James: roda periodicamente, sem intervencao humana.

    Usuarios com agent_enabled=False sao ignorados em todas as acoes.
    """
    async with database.AsyncSessionLocal() as db:
        promoted = await _promote_stale_drafts(db)
        refreshed = await _refresh_underperforming_campaigns(db)
        suggested = await _suggest_replicating_top_performers(db)
        await db.commit()

    return {
        "campanhas_promovidas": promoted,
        "campanhas_com_legenda_renovada": refreshed,
        "sugestoes_de_replicacao": suggested,
    }
