from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.user import User
from schemas import UserCreate, UserOut, Token
from security import hash_password, verify_password, create_access_token, get_current_user
from services import shopee_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token = create_access_token(subject=user.id)
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/shopee/connect")
async def shopee_connect():
    """Redireciona o usuário para a tela de autorização OAuth da Shopee."""
    url = shopee_service.build_authorization_url()
    return RedirectResponse(url)


@router.get("/callback")
async def shopee_callback(
    code: str,
    shop_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    token_data = await shopee_service.exchange_code_for_token(code, shop_id)
    current_user.shopee_access_token = token_data.get("access_token")
    current_user.shopee_refresh_token = token_data.get("refresh_token")
    current_user.shopee_shop_id = shop_id
    await db.commit()
    return RedirectResponse(f"{settings.FRONTEND_URL}/dashboard?shopee=connected")
