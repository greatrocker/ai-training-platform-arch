import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..security import require_role

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=list[schemas.GroupOut])
def list_groups(db: Session = Depends(get_db)):
    return db.query(models.Group).all()


@router.post("", response_model=schemas.GroupOut, dependencies=[Depends(require_role("admin"))])
def create_group(payload: schemas.GroupIn, db: Session = Depends(get_db)):
    group = models.Group(group_name=payload.group_name)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=204, dependencies=[Depends(require_role("admin"))])
def delete_group(group_id: uuid.UUID, db: Session = Depends(get_db)):
    group = db.get(models.Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="group not found")
    db.delete(group)
    db.commit()


@router.post("/{group_id}/roles/{role_id}", status_code=204, dependencies=[Depends(require_role("admin"))])
def assign_role_to_group(group_id: uuid.UUID, role_id: uuid.UUID, db: Session = Depends(get_db)):
    group = db.get(models.Group, group_id)
    role = db.get(models.Role, role_id)
    if not group or not role:
        raise HTTPException(status_code=404, detail="group or role not found")
    if role not in group.roles:
        group.roles.append(role)
        db.commit()


@router.delete("/{group_id}/roles/{role_id}", status_code=204, dependencies=[Depends(require_role("admin"))])
def unassign_role_from_group(group_id: uuid.UUID, role_id: uuid.UUID, db: Session = Depends(get_db)):
    group = db.get(models.Group, group_id)
    role = db.get(models.Role, role_id)
    if not group or not role:
        raise HTTPException(status_code=404, detail="group or role not found")
    if role in group.roles:
        group.roles.remove(role)
        db.commit()
