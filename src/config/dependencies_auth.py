from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import get_jwt_auth_manager
from database import UserModel, get_db, UserGroupEnum
from security.interfaces import JWTAuthManagerInterface

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
        session: AsyncSession = Depends(get_db),
) -> UserModel:
    try:
        payload = jwt_manager.decode_access_token(token)
        print(f"=== AUTH DEBUG ===")
        print(f"Payload: {payload}")
        user_email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        print(f"Looking for user - Email: {user_email}, ID: {user_id}")

    except Exception as e:
        print(f"Token decode error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired token")

    result = await session.execute(
        select(UserModel).options(selectinload(UserModel.cart)).where(UserModel.email == user_email)
    )
    user = result.scalar_one_or_none()
    print(f"User found: {user is not None}")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
