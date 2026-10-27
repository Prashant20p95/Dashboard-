from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from database import get_db
from models import AuditLog
from schemas import AuditLogResponse, PaginatedResponse

router = APIRouter()

def create_audit_log(db: Session, entity_name: str, entity_id: int, action: str, description: str, old_values=None, new_values=None, user_id=None):
    log = AuditLog(
        entity_name=entity_name,
        entity_id=entity_id,
        action=action,
        description=description,
        old_values_json=old_values,
        new_values_json=new_values,
        user_id=user_id
    )
    db.add(log)
    db.commit()
    return log

@router.get("/", response_model=PaginatedResponse)
def list_audit_logs(
    entity_name: Optional[str] = None,
    entity_id: Optional[int] = None,
    action: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    
    if entity_name:
        query = query.filter(AuditLog.entity_name == entity_name)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if action:
        query = query.filter(AuditLog.action == action)
        
    query = query.order_by(AuditLog.timestamp.desc())
        
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return PaginatedResponse(
        items=[AuditLogResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )

@router.get("/entity/{entity_name}/{entity_id}", response_model=list[AuditLogResponse])
def get_entity_audit_trail(entity_name: str, entity_id: int, db: Session = Depends(get_db)):
    items = db.query(AuditLog).filter(AuditLog.entity_name == entity_name, AuditLog.entity_id == entity_id).order_by(AuditLog.timestamp.desc()).all()
    return items
