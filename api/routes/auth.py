"""
Authentication routes for ESO Build Optimizer API.

Handles user registration, login, and token management.
"""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.security import (
    CurrentUser,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from api.models.database import User, get_db
from api.models.schemas import (
    ErrorResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# Registration
# =============================================================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid input or user already exists", "model": ErrorResponse},
    },
    summary="Register a new user",
    description="Create a new user account with email, username, and password.",
)
async def register(
    user_data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Register a new user.

    - **email**: Valid email address (must be unique)
    - **username**: Username (3-50 characters, must be unique)
    - **password**: Password (minimum 8 characters)
    """
    # Check if email already exists
    existing_email = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if existing_email.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if username already exists
    existing_username = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if existing_username.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    # Create new user
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
    )

    try:
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please try again.",
        )

    return UserResponse.model_validate(new_user)


# =============================================================================
# Login
# =============================================================================

@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials", "model": ErrorResponse},
    },
    summary="Login and get JWT token",
    description="Authenticate with email and password to receive a JWT access token.",
)
async def login(
    credentials: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Authenticate user and return JWT token.

    - **email**: Registered email address
    - **password**: Account password

    Returns an access token valid for the configured duration.
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Generate access token
    access_token = create_access_token(user.id)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


# =============================================================================
# Token Refresh
# =============================================================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        200: {"description": "Token refreshed successfully"},
        401: {"description": "Invalid or expired token", "model": ErrorResponse},
    },
    summary="Refresh access token",
    description="Get a new access token using the current valid token.",
)
async def refresh_token(
    current_user: CurrentUser,
) -> TokenResponse:
    """
    Refresh the access token for an authenticated user.

    Requires a valid Bearer token in the Authorization header.
    Returns a new access token with extended expiration.
    """
    # Generate new access token
    access_token = create_access_token(current_user.id)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


# =============================================================================
# Current User
# =============================================================================

@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        200: {"description": "Current user information"},
        401: {"description": "Not authenticated", "model": ErrorResponse},
    },
    summary="Get current user",
    description="Get information about the currently authenticated user.",
)
async def get_current_user_info(
    current_user: CurrentUser,
) -> UserResponse:
    """
    Get current authenticated user's information.

    Requires a valid Bearer token in the Authorization header.
    """
    return UserResponse.model_validate(current_user)


# =============================================================================
# Password Change
# =============================================================================

class PasswordChange(UserLogin):
    """Schema for password change request."""
    new_password: str = Field(..., min_length=8, max_length=128)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Password changed successfully"},
        400: {"description": "Invalid current password", "model": ErrorResponse},
        401: {"description": "Not authenticated", "model": ErrorResponse},
    },
    summary="Change password",
    description="Change the current user's password.",
)
async def change_password(
    password_data: PasswordChange,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Change the current user's password.

    - **email**: Must match current user's email
    - **password**: Current password for verification
    - **new_password**: New password (minimum 8 characters)
    """
    # Verify current password
    if not verify_password(password_data.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    current_user.hashed_password = hash_password(password_data.new_password)
    await db.commit()


# =============================================================================
# Account Deletion
# =============================================================================

@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Account deleted successfully"},
        401: {"description": "Not authenticated", "model": ErrorResponse},
    },
    summary="Delete account",
    description="Permanently delete the current user's account and all associated data.",
)
async def delete_account(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete the current user's account.

    This action is irreversible and will delete all associated data
    including combat runs and recommendations.
    """
    await db.delete(current_user)
    await db.commit()
