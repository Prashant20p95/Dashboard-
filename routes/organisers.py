from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import random
from typing import List, Optional

from database import get_db
from models import Organiser, EventDestination, Dispatch
from schemas import OrganiserCreate, OrganiserUpdate, OrganiserResponse, EventDestinationCreate, EventDestinationUpdate, EventDestinationResponse, PaginatedResponse
from routes.audit import create_audit_log

router = APIRouter()

def generate_destination_code():
    import uuid
    return f"ORG-{uuid.uuid4().hex[:8].upper()}"

@router.get("/by-state")
def get_organisers_by_state(db: Session = Depends(get_db)):
    counts = db.query(Organiser.state, func.count(Organiser.id)).group_by(Organiser.state).all()
    return [{"state": state, "count": count} for state, count in counts]

@router.get("/", response_model=PaginatedResponse)
def list_organisers(
    state: Optional[str] = None,
    district: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(Organiser)
    if state:
        query = query.filter(Organiser.state == state)
    if district:
        query = query.filter(Organiser.district == district)
    if search:
        query = query.filter(Organiser.organiser_name.ilike(f"%{search}%"))
        
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return PaginatedResponse(
        items=[OrganiserResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )

@router.get("/{id}", response_model=OrganiserResponse)
def get_organiser(id: int, db: Session = Depends(get_db)):
    item = db.query(Organiser).filter(Organiser.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Organiser not found")
    return item

@router.post("/", response_model=OrganiserResponse)
def create_organiser(org_in: OrganiserCreate, db: Session = Depends(get_db)):
    if not org_in.destination_code:
        org_in.destination_code = generate_destination_code()
        
    new_item = Organiser(**org_in.model_dump())
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    create_audit_log(db, "Organiser", new_item.id, "CREATE", f"Created organiser {new_item.organiser_name}")
    return new_item

@router.put("/{id}", response_model=OrganiserResponse)
def update_organiser(id: int, org_in: OrganiserUpdate, db: Session = Depends(get_db)):
    item = db.query(Organiser).filter(Organiser.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Organiser not found")
        
    for k, v in org_in.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
        
    db.commit()
    db.refresh(item)
    create_audit_log(db, "Organiser", item.id, "UPDATE", "Updated organiser details")
    return item

@router.delete("/{id}")
def delete_organiser(id: int, db: Session = Depends(get_db)):
    item = db.query(Organiser).filter(Organiser.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Organiser not found")
    
    dispatches_count = db.query(func.count(EventDestination.id)).filter(EventDestination.organiser_id == id).scalar()
    if dispatches_count and dispatches_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete organiser referenced by event destinations/dispatches")
        
    db.delete(item)
    db.commit()
    create_audit_log(db, "Organiser", id, "DELETE", "Deleted organiser")
    return {"detail": "Deleted"}


# EVENT DESTINATIONS SUB-ROUTES
@router.get("/destinations/by-state")
def get_destinations_by_state(event_id: int, db: Session = Depends(get_db)):
    counts = db.query(EventDestination.state, func.count(EventDestination.id)).filter(EventDestination.event_id == event_id).group_by(EventDestination.state).all()
    return [{"state": state, "count": count} for state, count in counts]

@router.get("/destinations/", response_model=List[EventDestinationResponse])
def list_destinations(event_id: int, db: Session = Depends(get_db)):
    items = db.query(EventDestination).filter(EventDestination.event_id == event_id).all()
    result = []
    for item in items:
        resp = EventDestinationResponse.model_validate(item)
        if item.required_quantities_json:
            resp.required_quantities = json.loads(item.required_quantities_json)
        result.append(resp)
    return result

@router.get("/destinations/{id}", response_model=EventDestinationResponse)
def get_destination(id: int, db: Session = Depends(get_db)):
    item = db.query(EventDestination).filter(EventDestination.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Event destination not found")
        
    resp = EventDestinationResponse.model_validate(item)
    if item.required_quantities_json:
        resp.required_quantities = json.loads(item.required_quantities_json)
    return resp

@router.post("/destinations/", response_model=EventDestinationResponse)
def create_destination(dest_in: EventDestinationCreate, db: Session = Depends(get_db)):
    data = dest_in.model_dump(exclude={'required_quantities'})
    
    if dest_in.organiser_id:
        org = db.query(Organiser).filter(Organiser.id == dest_in.organiser_id).first()
        if org:
            data['address_line1'] = data.get('address_line1') or org.address_line1
            data['address_line2'] = data.get('address_line2') or org.address_line2
            data['district'] = data.get('district') or org.district
            data['city'] = data.get('city') or org.city
            data['state'] = data.get('state') or org.state
            data['pin'] = data.get('pin') or org.pin
            
    if dest_in.required_quantities:
        data['required_quantities_json'] = json.dumps(dest_in.required_quantities)
        
    new_item = EventDestination(**data)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    create_audit_log(db, "EventDestination", new_item.id, "CREATE", f"Created event destination {new_item.destination_name}")
    
    resp = EventDestinationResponse.model_validate(new_item)
    if new_item.required_quantities_json:
        resp.required_quantities = json.loads(new_item.required_quantities_json)
    return resp

@router.post("/destinations/from-organiser", response_model=EventDestinationResponse)
def create_destination_from_organiser(event_id: int, organiser_id: int, db: Session = Depends(get_db)):
    org = db.query(Organiser).filter(Organiser.id == organiser_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organiser not found")
        
    new_item = EventDestination(
        event_id=event_id,
        organiser_id=organiser_id,
        destination_name=org.organiser_name,
        contact_person=org.contact_person,
        mobile=org.mobile,
        alt_phone=org.alt_phone,
        email=org.email,
        address_line1=org.address_line1,
        address_line2=org.address_line2,
        landmark=org.landmark,
        district=org.district,
        city=org.city,
        state=org.state,
        pin=org.pin
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    return EventDestinationResponse.model_validate(new_item)

@router.put("/destinations/{id}", response_model=EventDestinationResponse)
def update_destination(id: int, dest_in: EventDestinationUpdate, db: Session = Depends(get_db)):
    item = db.query(EventDestination).filter(EventDestination.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Event destination not found")
        
    for k, v in dest_in.model_dump(exclude={'required_quantities'}, exclude_unset=True).items():
        setattr(item, k, v)
        
    if dest_in.required_quantities is not None:
        item.required_quantities_json = json.dumps(dest_in.required_quantities)
        
    db.commit()
    db.refresh(item)
    
    create_audit_log(db, "EventDestination", item.id, "UPDATE", "Updated event destination details")
    
    resp = EventDestinationResponse.model_validate(item)
    if item.required_quantities_json:
        resp.required_quantities = json.loads(item.required_quantities_json)
    return resp

@router.delete("/destinations/{id}")
def delete_destination(id: int, db: Session = Depends(get_db)):
    item = db.query(EventDestination).filter(EventDestination.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Event destination not found")
        
    dispatches_count = db.query(func.count(Dispatch.id)).filter(Dispatch.destination_id == id).scalar()
    if dispatches_count and dispatches_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete destination referenced by dispatches")
        
    db.delete(item)
    db.commit()
    create_audit_log(db, "EventDestination", id, "DELETE", "Deleted event destination")
    return {"detail": "Deleted"}
