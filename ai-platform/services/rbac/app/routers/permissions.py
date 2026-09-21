from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..security import require_role

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("", response_model=list[schemas.PermissionOut])
def list_permissions(db: Session = Depends(get_db)):
    return db.query(models.Permission).all()


@router.post("", response_model=schemas.PermissionOut, dependencies=[Depends(require_role("admin"))])
def create_permission(payload: schemas.PermissionIn, db: Session = Depends(get_db)):
    perm = models.Permission(perm_key=payload.perm_key)
    db.add(perm)
    db.commit()
    db.refresh(perm)
    return perm
