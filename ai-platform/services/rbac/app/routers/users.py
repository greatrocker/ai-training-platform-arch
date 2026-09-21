import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..security import require_role

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.AppUser).all()


@router.post("", response_model=schemas.UserOut, dependencies=[Depends(require_role("admin"))])
def create_user(payload: schemas.UserIn, db: Session = Depends(get_db)):
    existing = db.query(models.AppUser).filter_by(oauth_sub=payload.oauth_sub).first()
    if existing:
        raise HTTPException(status_code=409, detail="user already exists")
    user = models.AppUser(**payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/groups/{group_id}", status_code=204, dependencies=[Depends(require_role("admin"))])
def assign_group_to_user(user_id: uuid.UUID, group_id: uuid.UUID, db: Session = Depends(get_db)):
    user = db.get(models.AppUser, user_id)
    group = db.get(models.Group, group_id)
    if not user or not group:
        raise HTTPException(status_code=404, detail="user or group not found")
    if group not in user.groups:
        user.groups.append(group)
        db.commit()


@router.delete("/{user_id}/groups/{group_id}", status_code=204, dependencies=[Depends(require_role("admin"))])
def unassign_group_from_user(user_id: uuid.UUID, group_id: uuid.UUID, db: Session = Depends(get_db)):
    user = db.get(models.AppUser, user_id)
    group = db.get(models.Group, group_id)
    if not user or not group:
        raise HTTPException(status_code=404, detail="user or group not found")
    if group in user.groups:
        user.groups.remove(group)
        db.commit()
