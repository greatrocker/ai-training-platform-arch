import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/pipeline/flows", tags=["logic-flows"])


@router.get("", response_model=list[schemas.LogicFlowOut])
def list_flows(db: Session = Depends(get_db)):
    return db.query(models.LogicFlow).order_by(models.LogicFlow.updated_at.desc()).all()


@router.post("", response_model=schemas.LogicFlowOut, status_code=201)
def create_flow(
    payload: schemas.LogicFlowIn,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None),
):
    flow = models.LogicFlow(
        name=payload.name,
        graph_json=payload.graph_json,
        created_by=x_user_id or "unknown",
        updated_at=datetime.now(timezone.utc),
    )
    db.add(flow)
    db.commit()
    db.refresh(flow)
    return flow


@router.get("/{flow_id}", response_model=schemas.LogicFlowOut)
def get_flow(flow_id: uuid.UUID, db: Session = Depends(get_db)):
    flow = db.get(models.LogicFlow, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="flow not found")
    return flow


@router.put("/{flow_id}", response_model=schemas.LogicFlowOut)
def update_flow(flow_id: uuid.UUID, payload: schemas.LogicFlowIn, db: Session = Depends(get_db)):
    flow = db.get(models.LogicFlow, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="flow not found")
    flow.name = payload.name
    flow.graph_json = payload.graph_json
    flow.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(flow)
    return flow


@router.delete("/{flow_id}", status_code=204)
def delete_flow(flow_id: uuid.UUID, db: Session = Depends(get_db)):
    flow = db.get(models.LogicFlow, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="flow not found")
    db.query(models.CctvDevice).filter(models.CctvDevice.bound_flow_id == flow_id).update({"bound_flow_id": None})
    db.delete(flow)
    db.commit()
