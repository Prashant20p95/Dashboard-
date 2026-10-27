from datetime import datetime, date
import random
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from database import get_db
from models import (
    DispatchBatch, Dispatch, DispatchItem, StockTransaction, EventDestination, Event,
    DeliveryConfirmation, AuditLog, CollateralItem
)
from schemas import (
    DispatchBatchCreate, DispatchBatchResponse, DispatchCreate, DispatchResponse,
    DispatchStatusUpdate, BulkDispatchCreate, PaginatedResponse
)

router = APIRouter()

def generate_code(prefix="DSP"):
    date_str = datetime.now().strftime("%Y%m%d")
    rnd = random.randint(1000, 9999)
    return f"{prefix}-{date_str}-{rnd}"

@router.post("/batches", response_model=DispatchBatchResponse)
def create_dispatch_batch(batch_in: DispatchBatchCreate, db: Session = Depends(get_db)):
    batch = DispatchBatch(
        batch_code=generate_code("DSP-BATCH"),
        event_id=batch_in.event_id,
        name=batch_in.name,
        notes=batch_in.notes,
        status="DRAFT"
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch

@router.get("/batches", response_model=PaginatedResponse)
def list_dispatch_batches(
    event_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    q = db.query(DispatchBatch)
    if event_id:
        q = q.filter(DispatchBatch.event_id == event_id)
    
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )

@router.get("/batches/{batch_id}", response_model=DispatchBatchResponse)
def get_dispatch_batch(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(DispatchBatch).filter(DispatchBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch

@router.put("/batches/{batch_id}", response_model=DispatchBatchResponse)
def update_dispatch_batch(batch_id: int, status: str, db: Session = Depends(get_db)):
    batch = db.query(DispatchBatch).filter(DispatchBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    batch.status = status
    db.commit()
    db.refresh(batch)
    return batch

@router.post("/", response_model=DispatchResponse)
def create_dispatch(
    dispatch_in: DispatchCreate, 
    db: Session = Depends(get_db)
):
    dest = db.query(EventDestination).filter(EventDestination.id == dispatch_in.destination_id, EventDestination.event_id == dispatch_in.event_id).first()
    if not dest:
        raise HTTPException(status_code=400, detail="Invalid destination or not part of this event")
    # Check for existing dispatches — warn but NEVER block (multiple shipments are valid)
    previous_dispatches = db.query(Dispatch).filter(
        Dispatch.event_id == dispatch_in.event_id,
        Dispatch.destination_id == dispatch_in.destination_id
    ).count()
    warning = None
    if previous_dispatches > 0:
        warning = f"{previous_dispatches} previous shipment(s) exist for this destination"

    for item_in in dispatch_in.items or []:
        pass

    dispatch = Dispatch(
        dispatch_code=generate_code("DSP"),
        batch_id=dispatch_in.batch_id,
        event_id=dispatch_in.event_id,
        destination_id=dispatch_in.destination_id,
        hist_organiser_name=dest.organiser.organiser_name if dest.organiser else None,
        hist_contact_person=dest.contact_person,
        hist_mobile=dest.mobile,
        hist_address_line1=dest.address_line1,
        hist_address_line2=dest.address_line2,
        hist_landmark=dest.landmark,
        hist_district=dest.district,
        hist_city=dest.city,
        hist_state=dest.state,
        hist_pin=dest.pin,
        dispatch_date=dispatch_in.dispatch_date,
        courier_partner=dispatch_in.courier_partner,
        courier_name_other=dispatch_in.courier_name_other,
        awb_number=dispatch_in.awb_number,
        via=dispatch_in.via or "Surface",
        box_count=dispatch_in.box_count or "1 Box",
        courier_status=dispatch_in.courier_status or "IN_TRANSIT",
        actual_delivery_date=(dispatch_in.dispatch_date or date.today()) if dispatch_in.courier_status == "DELIVERED" else None,
        expected_delivery_date=dispatch_in.expected_delivery_date,
        notes=dispatch_in.notes
    )
    db.add(dispatch)
    db.flush()

    for item_in in dispatch_in.items:
        di = DispatchItem(dispatch_id=dispatch.id, collateral_code=item_in.collateral_code, quantity=item_in.quantity)
        db.add(di)
        db.flush()

        stock_before = db.query(func.sum(StockTransaction.quantity)).filter(
            StockTransaction.event_id == dispatch_in.event_id,
            StockTransaction.collateral_code == item_in.collateral_code
        ).scalar() or 0
        
        st = StockTransaction(
            event_id=dispatch_in.event_id,
            collateral_code=item_in.collateral_code,
            transaction_type="DISPATCH",
            quantity=-item_in.quantity,
            balance_after=stock_before - item_in.quantity,
            reference_type="DISPATCH_ITEM",
            reference_id=di.id,
        )
        db.add(st)
    
    audit = AuditLog(
        entity_name="Dispatch",
        entity_id=dispatch.id,
        action="CREATE",
        description=f"Created dispatch {dispatch.dispatch_code}"
    )
    db.add(audit)
    db.commit()
    db.refresh(dispatch)
    return dispatch

@router.post("/bulk")
def create_bulk_dispatch(bulk_in: BulkDispatchCreate, db: Session = Depends(get_db)):
    stock_reqs = {}
    for entry in bulk_in.entries:
        for item in entry.items:
            stock_reqs[item.collateral_code] = stock_reqs.get(item.collateral_code, 0) + item.quantity
    
    for code, total_req in stock_reqs.items():
        avail = db.query(func.sum(StockTransaction.quantity)).filter(
            StockTransaction.event_id == bulk_in.event_id,
            StockTransaction.collateral_code == code
        ).scalar() or 0
        if avail < total_req:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {code}. Requested total: {total_req}, Available: {avail}")
            
    dispatches = []
    for entry in bulk_in.entries:
        dest = db.query(EventDestination).filter(EventDestination.id == entry.destination_id).first()
        if not dest:
            raise HTTPException(status_code=400, detail=f"Destination {entry.destination_id} not found")
        dispatch = Dispatch(
            dispatch_code=generate_code("DSP"),
            batch_id=bulk_in.batch_id,
            event_id=bulk_in.event_id,
            destination_id=entry.destination_id,
            hist_organiser_name=dest.organiser.organiser_name if dest.organiser else None,
            hist_contact_person=dest.contact_person,
            hist_mobile=dest.mobile,
            hist_address_line1=dest.address_line1,
            hist_address_line2=dest.address_line2,
            hist_landmark=dest.landmark,
            hist_district=dest.district,
            hist_city=dest.city,
            hist_state=dest.state,
            hist_pin=dest.pin,
            dispatch_date=bulk_in.dispatch_date,
            courier_partner=bulk_in.courier_partner
        )
        db.add(dispatch)
        db.flush()
        
        for item_in in entry.items:
            di = DispatchItem(dispatch_id=dispatch.id, collateral_code=item_in.collateral_code, quantity=item_in.quantity)
            db.add(di)
            db.flush()
            
            stock_before = db.query(func.sum(StockTransaction.quantity)).filter(
                StockTransaction.event_id == bulk_in.event_id,
                StockTransaction.collateral_code == item_in.collateral_code
            ).scalar() or 0
            
            st = StockTransaction(
                event_id=bulk_in.event_id,
                collateral_code=item_in.collateral_code,
                transaction_type="DISPATCH",
                quantity=-item_in.quantity,
                balance_after=stock_before - item_in.quantity,
                reference_type="DISPATCH_ITEM",
                reference_id=di.id,
            )
            db.add(st)
        dispatches.append(dispatch)
        
    db.commit()
    return {"message": f"Created {len(dispatches)} dispatches."}

@router.get("/", response_model=PaginatedResponse)
def list_dispatches(
    event_id: Optional[int] = None,
    destination_id: Optional[int] = None,
    batch_id: Optional[int] = None,
    state: Optional[str] = None,
    courier_status: Optional[str] = None,
    courier_partner: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    q = db.query(Dispatch)
    if event_id:
        q = q.filter(Dispatch.event_id == event_id)
    if destination_id:
        q = q.filter(Dispatch.destination_id == destination_id)
    if batch_id:
        q = q.filter(Dispatch.batch_id == batch_id)
    if state:
        q = q.filter(Dispatch.hist_state == state)
    if courier_status:
        q = q.filter(Dispatch.courier_status == courier_status)
    if courier_partner:
        q = q.filter(Dispatch.courier_partner == courier_partner)
        
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    
    return PaginatedResponse(
        items=[DispatchResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )

@router.get("/{dispatch_id}", response_model=DispatchResponse)
def get_dispatch(dispatch_id: int, db: Session = Depends(get_db)):
    dispatch = db.query(Dispatch).filter(Dispatch.id == dispatch_id).first()
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return dispatch

@router.put("/{dispatch_id}", response_model=DispatchResponse)
def update_dispatch(dispatch_id: int, status_update: DispatchStatusUpdate, db: Session = Depends(get_db)):
    dispatch = db.query(Dispatch).filter(Dispatch.id == dispatch_id).first()
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    
    if status_update.courier_status: dispatch.courier_status = status_update.courier_status
    if status_update.courier_partner: dispatch.courier_partner = status_update.courier_partner
    if status_update.courier_name_other: dispatch.courier_name_other = status_update.courier_name_other
    if status_update.awb_number: dispatch.awb_number = status_update.awb_number
    if status_update.via is not None: dispatch.via = status_update.via
    if status_update.box_count is not None: dispatch.box_count = status_update.box_count
    if status_update.dispatch_date: dispatch.dispatch_date = status_update.dispatch_date
    if status_update.expected_delivery_date: dispatch.expected_delivery_date = status_update.expected_delivery_date
    if status_update.actual_delivery_date: dispatch.actual_delivery_date = status_update.actual_delivery_date
    if status_update.notes is not None: dispatch.notes = status_update.notes
    
    if status_update.items is not None:
        for old_item in list(dispatch.items):
            db.delete(old_item)
        for item_in in status_update.items:
            di = DispatchItem(dispatch_id=dispatch.id, collateral_code=item_in.collateral_code, quantity=item_in.quantity)
            db.add(di)
    
    db.commit()
    db.refresh(dispatch)
    return dispatch

from pydantic import BaseModel

class OutmailRequest(BaseModel):
    recipient_email: str
    cc_email: Optional[str] = None
    subject: str
    body: str

@router.post("/{dispatch_id}/outmail")
def send_dispatch_outmail(
    dispatch_id: int, 
    outmail_in: OutmailRequest, 
    db: Session = Depends(get_db)
):
    dispatch = db.query(Dispatch).filter(Dispatch.id == dispatch_id).first()
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    
    audit = AuditLog(
        action="OUTMAIL_SENT",
        entity_name="DISPATCH",
        entity_id=dispatch_id,
        description=f"Delivery confirmation outmail sent to {outmail_in.recipient_email} (Subject: {outmail_in.subject})",
        timestamp=datetime.now()
    )
    db.add(audit)
    
    note_stamp = f"[Delivery Outmail sent to {outmail_in.recipient_email} on {datetime.now().strftime('%Y-%m-%d %H:%M')}]"
    dispatch.notes = f"{dispatch.notes}\n{note_stamp}" if dispatch.notes else note_stamp
    db.commit()
    return {"status": "SUCCESS", "message": f"Delivery outmail recorded for {outmail_in.recipient_email}"}

@router.post("/destinations/{destination_id}/outmail")
def send_destination_outmail(
    destination_id: int,
    outmail_in: OutmailRequest,
    db: Session = Depends(get_db)
):
    dest = db.query(EventDestination).filter(EventDestination.id == destination_id).first()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    audit = AuditLog(
        action="OUTMAIL_SENT",
        entity_name="EVENT_DESTINATION",
        entity_id=destination_id,
        description=f"Delivery confirmation outmail sent to {outmail_in.recipient_email} for station {dest.destination_name}",
        timestamp=datetime.now()
    )
    db.add(audit)
    db.commit()
    return {"status": "SUCCESS", "message": f"Delivery outmail recorded for station {dest.destination_name}"}

