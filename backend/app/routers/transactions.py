from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from backend.app.activity import record_activity
from backend.app.db.database import get_db
from backend.app.dependencies import get_current_regular_user
from backend.app.models import Transaction, User
from backend.app.schemas import TransactionCreate, TransactionUpdate, TransactionResponse

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.get("", response_model=list[TransactionResponse])
def list_transactions(db: Session = Depends(get_db), user: User = Depends(get_current_regular_user)):
    return db.query(Transaction).filter(Transaction.user_id == user.id).order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).all()

@router.post("", response_model=TransactionResponse, status_code=201)
def create_transaction(data: TransactionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_regular_user)):
    transaction = Transaction(**data.model_dump(), user_id=user.id)
    db.add(transaction)
    db.flush()
    record_activity(
        db,
        "transaction_created",
        actor_user_id=user.id,
        target_user_id=user.id,
        details=f"Transaction #{transaction.id} created",
    )
    db.commit()
    db.refresh(transaction)
    return transaction

@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(transaction_id: int, data: TransactionUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_regular_user)):
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == user.id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(transaction, key, value)
    record_activity(
        db,
        "transaction_updated",
        actor_user_id=user.id,
        target_user_id=user.id,
        details=f"Transaction #{transaction.id} updated",
    )
    db.commit()
    db.refresh(transaction)
    return transaction

@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_regular_user)):
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == user.id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    record_activity(
        db,
        "transaction_deleted",
        actor_user_id=user.id,
        target_user_id=user.id,
        details=f"Transaction #{transaction.id} deleted",
    )
    db.delete(transaction)
    db.commit()
    return Response(status_code=204)
