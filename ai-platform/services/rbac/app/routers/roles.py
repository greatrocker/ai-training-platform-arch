import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..security import require_role

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[schemas.RoleOut])
def list_roles(db: Session = Depends(get_db)):
    return db.query(models.Role).all()


@router.post("", response_model=schemas.RoleOut, dependencies=[Depends(require_role("admin"))])
def create_role(payload: schemas.RoleIn, db: Session = Depends(get_db)):
    role = models.Role(role_name=payload.role_name)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.delete("/{role_id}", status_code=204, dependencies=[Depends(require_role("admin"))])
def delete_role(role_id: uuid.UUID, db: Session = Depends(get_db)):
    role = db.get(models.Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="role not found")
    db.delete(role)
    db.commit()


@router.post("/{role_id}/permissions/{perm_id}", status_code=204, dependencies=[Depends(require_role("admin"))])
def assign_permission_to_role(role_id: uuid.UUID, perm_id: uuid.UUID, db: Session = Depends(get_db)):
    role = db.get(models.Role, role_id)
    perm = db.get(models.Permission, perm_id)
    if not role or not perm:
        raise HTTPException(status_code=404, detail="role or permission not found")
    if perm not in role.permissions:
        role.permissions.append(perm)
        db.commit()


@router.delete("/{role_id}/permissions/{perm_id}", status_code=204, dependencies=[Depends(require_role("admin"))])
def unassign_permission_from_role(role_id: uuid.UUID, perm_id: uuid.UUID, db: Session = Depends(get_db)):
    role = db.get(models.Role, role_id)
    perm = db.get(models.Permission, perm_id)
    if not role or not perm:
        raise HTTPException(status_code=404, detail="role or permission not found")
    if perm in role.permissions:
        role.permissions.remove(perm)
        db.commit()
