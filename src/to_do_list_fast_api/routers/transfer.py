from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette import status

from to_do_list_fast_api.database import get_db
from to_do_list_fast_api.dependencies import get_current_user
from to_do_list_fast_api.models import Transfer, User
from to_do_list_fast_api.schemas import DataResponse, TransferCreate, TransferResponse

router = APIRouter(prefix="/transfer", tags=["Transfer"])


@router.post(
    "",
    response_model=DataResponse[TransferResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Transfer balance to another user",
)
async def create_transfer(
    transfer_in: TransferCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DataResponse[TransferResponse]:
    if transfer_in.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transfer to yourself",
        )

    receiver = db.query(User).filter(User.id == transfer_in.user_id).first()
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {transfer_in.user_id} not found",
        )

    if not receiver.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipient user account is inactive",
        )

    if current_user.balance < transfer_in.nominal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance",
        )

    current_user.balance -= transfer_in.nominal
    receiver.balance += transfer_in.nominal

    new_transfer = Transfer(
        sender_id=current_user.id,
        receiver_id=receiver.id,
        nominal=transfer_in.nominal,
        transaction_type=transfer_in.transaction_type,
        transaction_purpose=transfer_in.transaction_purpose,
    )
    db.add(new_transfer)
    db.commit()
    db.refresh(new_transfer)
    db.refresh(current_user)

    return DataResponse(
        status=status.HTTP_201_CREATED,
        message="Transfer completed successfully",
        data=TransferResponse(
            id=new_transfer.id,
            sender_id=new_transfer.sender_id,
            user_id=new_transfer.receiver_id,
            nominal=new_transfer.nominal,
            transaction_type=new_transfer.transaction_type,
            transaction_purpose=new_transfer.transaction_purpose,
            sender_balance=current_user.balance,
            created_at=new_transfer.created_at,
        ),
    )
