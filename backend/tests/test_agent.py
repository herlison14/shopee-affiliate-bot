from datetime import timedelta

import pytest
from sqlalchemy import select

import database
from models.agent_action import AgentAction
from models.campaign import Campaign
from models.commission import Commission
from models.user import User
from security import hash_password
from services.agent_service import run_agent_cycle

pytestmark = pytest.mark.anyio


async def _create_user(db, *, email="agentuser@example.com", agent_enabled=True) -> User:
    user = User(email=email, hashed_password=hash_password("senha123456"), agent_enabled=agent_enabled)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def test_promotes_stale_draft_campaign():
    async with database.AsyncSessionLocal() as db:
        user = await _create_user(db)
        old_draft = Campaign(
            user_id=user.id,
            product_name="Produto antigo em draft",
            product_url="https://shopee.com.br/x",
            status="draft",
            created_at=database.utcnow() - timedelta(hours=48),
        )
        recent_draft = Campaign(
            user_id=user.id,
            product_name="Produto recente em draft",
            product_url="https://shopee.com.br/y",
            status="draft",
            created_at=database.utcnow(),
        )
        db.add_all([old_draft, recent_draft])
        await db.commit()
        old_id, recent_id = old_draft.id, recent_draft.id

    result = await run_agent_cycle()
    assert result["campanhas_promovidas"] == 1

    async with database.AsyncSessionLocal() as db:
        old_campaign = await db.get(Campaign, old_id)
        recent_campaign = await db.get(Campaign, recent_id)
        assert old_campaign.status == "scheduled"
        assert recent_campaign.status == "draft"

        actions = (await db.execute(select(AgentAction).where(AgentAction.campaign_id == old_id))).scalars().all()
        assert len(actions) == 1
        assert actions[0].action_type == "promover_draft"


async def test_refreshes_underperforming_campaign_once():
    async with database.AsyncSessionLocal() as db:
        user = await _create_user(db)
        stale = Campaign(
            user_id=user.id,
            product_name="Sem vendas ha uma semana",
            product_url="https://shopee.com.br/z",
            status="scheduled",
            caption="legenda antiga",
            hashtags="#antiga",
            created_at=database.utcnow() - timedelta(days=10),
        )
        with_sale = Campaign(
            user_id=user.id,
            product_name="Com venda confirmada",
            product_url="https://shopee.com.br/w",
            status="scheduled",
            caption="legenda antiga 2",
            hashtags="#antiga2",
            created_at=database.utcnow() - timedelta(days=10),
        )
        db.add_all([stale, with_sale])
        await db.commit()
        stale_id, with_sale_id = stale.id, with_sale.id

        db.add(
            Commission(
                campaign_id=with_sale_id,
                order_id="PED123",
                sale_amount=100,
                commission_amount=10,
                platform_fee=2,
            )
        )
        await db.commit()

    result = await run_agent_cycle()
    assert result["campanhas_com_legenda_renovada"] == 1

    async with database.AsyncSessionLocal() as db:
        stale_campaign = await db.get(Campaign, stale_id)
        sold_campaign = await db.get(Campaign, with_sale_id)
        assert stale_campaign.caption != "legenda antiga"
        assert sold_campaign.caption == "legenda antiga 2"

    # roda de novo: nao deve duplicar a acao nem regenerar de novo
    result2 = await run_agent_cycle()
    assert result2["campanhas_com_legenda_renovada"] == 0

    async with database.AsyncSessionLocal() as db:
        actions = (
            await db.execute(select(AgentAction).where(AgentAction.campaign_id == stale_id))
        ).scalars().all()
        assert len(actions) == 1


async def test_ignores_users_with_agent_disabled():
    async with database.AsyncSessionLocal() as db:
        user = await _create_user(db, email="disableduser@example.com", agent_enabled=False)
        old_draft = Campaign(
            user_id=user.id,
            product_name="Draft de usuario com agente desligado",
            product_url="https://shopee.com.br/disabled",
            status="draft",
            created_at=database.utcnow() - timedelta(hours=48),
        )
        db.add(old_draft)
        await db.commit()
        draft_id = old_draft.id

    result = await run_agent_cycle()
    assert result["campanhas_promovidas"] == 0

    async with database.AsyncSessionLocal() as db:
        draft = await db.get(Campaign, draft_id)
        assert draft.status == "draft"


async def test_suggests_replicating_campaign_with_sale_once():
    async with database.AsyncSessionLocal() as db:
        user = await _create_user(db, email="topperformer@example.com")
        campaign = Campaign(
            user_id=user.id,
            product_name="Produto que vendeu bem",
            product_url="https://shopee.com.br/sucesso",
            status="posted",
        )
        db.add(campaign)
        await db.commit()
        campaign_id = campaign.id

        db.add(
            Commission(
                campaign_id=campaign_id,
                order_id="PED-SUCESSO",
                sale_amount=200,
                commission_amount=20,
                platform_fee=4,
            )
        )
        await db.commit()

    result = await run_agent_cycle()
    assert result["sugestoes_de_replicacao"] == 1

    result2 = await run_agent_cycle()
    assert result2["sugestoes_de_replicacao"] == 0

    async with database.AsyncSessionLocal() as db:
        actions = (
            await db.execute(
                select(AgentAction).where(
                    AgentAction.campaign_id == campaign_id, AgentAction.action_type == "sugerir_replicar"
                )
            )
        ).scalars().all()
        assert len(actions) == 1
