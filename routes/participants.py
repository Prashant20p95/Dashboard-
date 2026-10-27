from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
from typing import List, Optional

from database import get_db
from models import Participant
from schemas import ParticipantCreate, ParticipantUpdate, ParticipantResponse, PaginatedResponse

router = APIRouter()

@router.get("/", response_model=PaginatedResponse)
def list_participants(
    event_id: int, 
    card_type: Optional[str] = None, 
    search: Optional[str] = None, 
    page: int = 1, 
    page_size: int = 50, 
    db: Session = Depends(get_db)
):
    query = db.query(Participant).filter(Participant.event_id == event_id)
    
    if card_type:
        query = query.filter(Participant.card_type == card_type)
    if search:
        query = query.filter((Participant.full_name.ilike(f"%{search}%")) | (Participant.mobile.ilike(f"%{search}%")))
        
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    result_items = []
    for item in items:
        resp = ParticipantResponse.model_validate(item)
        if item.custom_fields_json:
            resp.custom_fields = json.loads(item.custom_fields_json)
        result_items.append(resp)
        
    return PaginatedResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )

@router.get("/count")
def get_participant_count(event_id: int, card_type: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(func.count(Participant.id)).filter(Participant.event_id == event_id)
    if card_type:
        query = query.filter(Participant.card_type == card_type)
    return {"count": query.scalar() or 0}

@router.get("/{id}", response_model=ParticipantResponse)
def get_participant(id: int, db: Session = Depends(get_db)):
    item = db.query(Participant).filter(Participant.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    resp = ParticipantResponse.model_validate(item)
    if item.custom_fields_json:
        resp.custom_fields = json.loads(item.custom_fields_json)
    return resp

@router.post("/", response_model=ParticipantResponse)
def create_participant(part_in: ParticipantCreate, db: Session = Depends(get_db)):
    data = part_in.model_dump(exclude={'custom_fields'})
    if part_in.custom_fields:
        data['custom_fields_json'] = json.dumps(part_in.custom_fields)
        
    new_item = Participant(**data)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    resp = ParticipantResponse.model_validate(new_item)
    if new_item.custom_fields_json:
        resp.custom_fields = json.loads(new_item.custom_fields_json)
    return resp

@router.post("/bulk")
def bulk_create_participants(participants: List[ParticipantCreate], db: Session = Depends(get_db)):
    new_items = []
    for part_in in participants:
        data = part_in.model_dump(exclude={'custom_fields'})
        if part_in.custom_fields:
            data['custom_fields_json'] = json.dumps(part_in.custom_fields)
        new_items.append(Participant(**data))
        
    db.bulk_save_objects(new_items)
    db.commit()
    return {"created_count": len(new_items)}

@router.put("/{id}", response_model=ParticipantResponse)
def update_participant(id: int, part_in: ParticipantUpdate, db: Session = Depends(get_db)):
    item = db.query(Participant).filter(Participant.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Participant not found")
        
    for k, v in part_in.model_dump(exclude={'custom_fields'}, exclude_unset=True).items():
        setattr(item, k, v)
        
    if part_in.custom_fields is not None:
        item.custom_fields_json = json.dumps(part_in.custom_fields)
        
    db.commit()
    db.refresh(item)
    
    resp = ParticipantResponse.model_validate(item)
    if item.custom_fields_json:
        resp.custom_fields = json.loads(item.custom_fields_json)
    return resp

@router.delete("/{id}")
def delete_participant(id: int, db: Session = Depends(get_db)):
    item = db.query(Participant).filter(Participant.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Participant not found")
        
    db.delete(item)
    db.commit()
    return {"detail": "Deleted"}
