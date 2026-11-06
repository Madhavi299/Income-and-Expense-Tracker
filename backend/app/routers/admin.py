from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session, aliased

from backend.app.activity import record_activity
from backend.app.db.database import get_db
from backend.app.dependencies import get_current_admin
from backend.app.models import ActivityLog, Transaction, User
from backend.app.schemas import (
    ActivityResponse,
    AdminUserResponse,
    AdminUserSummary,
    AdminUserUpdate,
)

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/users", response_model=list[AdminUserSummary])
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    del admin
    rows = (
        db.query(
            User,
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.transaction_type == "Income", Transaction.amount),
                        else_=0.0,
                    )
                ),
                0.0,
            ).label("total_income"),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.transaction_type == "Expense", Transaction.amount),
                        else_=0.0,
                    )
                ),
                0.0,
            ).label("total_expenses"),
        )
        .outerjoin(Transaction, Transaction.user_id == User.id)
        .group_by(User.id)
        .order_by(User.created_at.desc(), User.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        AdminUserSummary(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            total_income=total_income,
            total_expenses=total_expenses,
            balance=total_income - total_expenses,
        )
        for user, total_income, total_expenses in rows
    ]


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: int,
    data: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    changes = data.model_dump(exclude_unset=True)
    if not changes or any(value is None for value in changes.values()):
        raise HTTPException(status_code=422, detail="Provide a role and/or active status")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")
    if user.id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot change your own role or active status",
        )

    new_role = changes.get("role", user.role)
    new_active = changes.get("is_active", user.is_active)
    removes_active_admin = (
        user.role == "admin"
        and user.is_active
        and (new_role != "admin" or not new_active)
    )
    if removes_active_admin:
        active_admins = (
            db.query(User.id)
            .filter(User.role == "admin", User.is_active.is_(True))
            .with_for_update()
            .all()
        )
        if len(active_admins) <= 1:
            raise HTTPException(
                status_code=400,
                detail="The last active administrator cannot be deactivated or demoted",
            )

    previous_role = user.role
    previous_active = user.is_active
    for key, value in changes.items():
        setattr(user, key, value)
    details = (
        f"role: {previous_role} -> {user.role}; "
        f"active: {previous_active} -> {user.is_active}"
    )
    record_activity(
        db,
        "user_account_updated",
        actor_user_id=admin.id,
        target_user_id=user.id,
        details=details,
    )
    db.commit()
    db.refresh(user)
    return user


@router.get("/activity", response_model=list[ActivityResponse])
def list_activity(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
    limit: int = Query(default=100, ge=1, le=500),
):
    del admin
    actor = aliased(User)
    target = aliased(User)
    rows = (
        db.query(ActivityLog, actor.username, target.username)
        .outerjoin(actor, ActivityLog.actor_user_id == actor.id)
        .outerjoin(target, ActivityLog.target_user_id == target.id)
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .limit(limit)
        .all()
    )
    return [
        ActivityResponse(
            id=event.id,
            actor_user_id=event.actor_user_id,
            actor_username=actor_username,
            target_user_id=event.target_user_id,
            target_username=target_username,
            action=event.action,
            details=event.details,
            created_at=event.created_at,
        )
        for event, actor_username, target_username in rows
    ]
