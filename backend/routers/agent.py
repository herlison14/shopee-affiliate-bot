from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.agent_action import AgentAction
from models.user import User
from schemas import AgentActionOut
from security import get_current_user

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.get("/actions", response_model=list[AgentActionOut])
async def list_agent_actions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
):
    """Historico de acoes que o agente James tomou automaticamente."""
    result = await db.execute(
        select(AgentAction)
        .where(AgentAction.user_id == current_user.id)
        .order_by(AgentAction.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
