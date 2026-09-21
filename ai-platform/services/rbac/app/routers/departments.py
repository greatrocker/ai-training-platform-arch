import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..security import require_role

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=list[schemas.DepartmentOut])
def list_departments(db: Session = Depends(get_db)):
    return db.query(models.Department).all()


@router.post("", response_model=schemas.DepartmentOut, dependencies=[Depends(require_role("admin"))])
def create_department(payload: schemas.DepartmentIn, db: Session = Depends(get_db)):
    dept = models.Department(dept_name=payload.dept_name)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.delete("/{dept_id}", status_code=204, dependencies=[Depends(require_role("admin"))])
def delete_department(dept_id: uuid.UUID, db: Session = Depends(get_db)):
    dept = db.get(models.Department, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="department not found")
    db.delete(dept)
    db.commit()
