from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette import status

from to_do_list_fast_api.database import get_db
from to_do_list_fast_api.dependencies import get_current_user
from to_do_list_fast_api.models import User, UserFavorite
from to_do_list_fast_api.schemas import DataResponse, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


def _to_user_response(user: User, is_favorite: bool) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        balance=user.balance,
        is_favorite=is_favorite,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.get(
    "",
    response_model=DataResponse[list[UserResponse]],
    status_code=status.HTTP_200_OK,
    summary="Get all users excluding current user and favorited users",
)
async def get_all_users(
    search: str | None = Query(
        default=None, description="Search term for username or email"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DataResponse[list[UserResponse]]:
    favorite_subquery = select(UserFavorite.favorite_user_id).where(
        UserFavorite.user_id == current_user.id
    )
    query = db.query(User).filter(
        User.id != current_user.id,
        ~User.id.in_(favorite_subquery),
    )

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (User.username.ilike(search_filter)) | (User.email.ilike(search_filter))
        )

    users = query.order_by(User.id.asc()).all()
    return DataResponse(
        status=status.HTTP_200_OK,
        message="Users retrieved successfully",
        data=[_to_user_response(u, is_favorite=False) for u in users],
    )


@router.get(
    "/favorites",
    response_model=DataResponse[list[UserResponse]],
    status_code=status.HTTP_200_OK,
    summary="Get all users favorited by the current user",
)
async def get_favorite_users(
    search: str | None = Query(
        default=None, description="Search term for username or email"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DataResponse[list[UserResponse]]:
    query = (
        db.query(User)
        .join(UserFavorite, User.id == UserFavorite.favorite_user_id)
        .filter(UserFavorite.user_id == current_user.id)
    )

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (User.username.ilike(search_filter)) | (User.email.ilike(search_filter))
        )

    users = query.order_by(UserFavorite.created_at.desc()).all()
    return DataResponse(
        status=status.HTTP_200_OK,
        message="Favorite users retrieved successfully",
        data=[_to_user_response(u, is_favorite=True) for u in users],
    )


@router.patch(
    "/favorites/{user_id}",
    response_model=DataResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Toggle favorite status for a target user",
)
async def toggle_favorite_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DataResponse[UserResponse]:
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot favorite yourself",
        )

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    existing_favorite = (
        db.query(UserFavorite)
        .filter(
            UserFavorite.user_id == current_user.id,
            UserFavorite.favorite_user_id == user_id,
        )
        .first()
    )

    if existing_favorite:
        db.delete(existing_favorite)
        db.commit()
        is_favorite = False
        message = "User removed from favorites successfully"
    else:
        new_favorite = UserFavorite(
            user_id=current_user.id,
            favorite_user_id=user_id,
        )
        db.add(new_favorite)
        db.commit()
        is_favorite = True
        message = "User added to favorites successfully"

    return DataResponse(
        status=status.HTTP_200_OK,
        message=message,
        data=_to_user_response(target_user, is_favorite=is_favorite),
    )
