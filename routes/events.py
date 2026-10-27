from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
import random
from typing import List, Optional

from database import get_db
from models import Event, Participant, EventDestination, Dispatch, DispatchItem, StockTransaction, DeliveryConfirmation, Organiser, PrintingJob, PhysicalReceipt, PrintingInvoice, CourierInvoice
from schemas import EventCreate, EventUpdate, EventResponse, EventSummary, PaginatedResponse, EventOperationalSummary, DestinationStatusSummary, DestinationDispatchItem
import json
from routes.audit import create_audit_log

router = APIRouter()

def generate_event_code():
    return f"EVT-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

@router.get("/calendar/upcoming", response_model=List[EventSummary])
def list_upcoming_events(db: Session = Depends(get_db)):
    events = db.query(Event).filter(Event.start_date >= date.today()).order_by(Event.start_date.asc()).all()
    summaries = []
    for e in events:
        summaries.append(EventSummary(
            id=e.id,
            event_code=e.event_code,
            name=e.name,
            city=e.city,
            state=e.state,
            start_date=e.start_date,
            end_date=e.end_date,
            delivery_deadline=e.delivery_deadline,
            status=e.status,
            participant_count=db.query(func.count(Participant.id)).filter(Participant.event_id == e.id).scalar() or 0,
            destination_count=db.query(func.count(EventDestination.id)).filter(EventDestination.event_id == e.id).scalar() or 0,
            dispatch_count=db.query(func.count(Dispatch.id)).filter(Dispatch.event_id == e.id).scalar() or 0,
            pending_confirmations=db.query(func.count(DeliveryConfirmation.id)).join(Dispatch).filter(Dispatch.event_id == e.id, DeliveryConfirmation.confirmation_status == 'PENDING').scalar() or 0
        ))
    return summaries

@router.get("/{id}/summary", response_model=EventOperationalSummary)
def get_event_summary(id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    participant_count = db.query(func.count(Participant.id)).filter(Participant.event_id == id).scalar() or 0
    destinations = db.query(EventDestination).filter(EventDestination.event_id == id).all()
    
    # Pre-fetch dispatches
    all_dispatches = db.query(Dispatch).filter(Dispatch.event_id == id).all()
    dispatch_items = db.query(DispatchItem).join(Dispatch).filter(Dispatch.event_id == id).all()
    confirmations = db.query(DeliveryConfirmation).join(Dispatch).filter(Dispatch.event_id == id).all()
    
    dispatch_by_dest = {}
    items_by_dispatch = {}
    conf_by_dispatch = {}
    
    for item in dispatch_items:
        items_by_dispatch.setdefault(item.dispatch_id, {})[item.collateral_code] = item.quantity
        
    for conf in confirmations:
        conf_by_dispatch[conf.dispatch_id] = {
            "status": conf.confirmation_status,
            "date": str(conf.confirmation_date).split()[0] if conf.confirmation_date else None,
            "by": conf.confirmed_by_name
        }
        
    for d in all_dispatches:
        dispatch_by_dest.setdefault(d.destination_id, []).append(d)
        
    dest_summaries = []
    
    for dest in destinations:
        required_qty = dest.required_quantities or {}
        dest_dispatches = dispatch_by_dest.get(dest.id, [])
        
        sent_qty = {}
        for d in dest_dispatches:
            d_items = items_by_dispatch.get(d.id, {})
            for code, qty in d_items.items():
                sent_qty[code] = sent_qty.get(code, 0) + qty
                
        remaining_qty = {}
        for code, req in required_qty.items():
            sent = sent_qty.get(code, 0)
            if req - sent > 0:
                remaining_qty[code] = req - sent
                
        # Calculate fulfillment
        fulfillment = "NOT_STARTED"
        if not required_qty:
            if dest_dispatches:
                fulfillment = "DISPATCHED"
        else:
            if not dest_dispatches:
                fulfillment = "NOT_STARTED"
            else:
                is_complete = True
                is_over = False
                for code, req in required_qty.items():
                    sent = sent_qty.get(code, 0)
                    if sent < req:
                        is_complete = False
                    if sent > req:
                        is_over = True
                
                if is_complete:
                    fulfillment = "OVER_DISPATCHED" if is_over else "COMPLETE"
                else:
                    fulfillment = "PARTIAL"
                    
        latest_dispatch = None
        if dest_dispatches:
            latest_dispatch = max(dest_dispatches, key=lambda x: (x.dispatch_date or date.min, x.id))
            
        organiser = db.query(Organiser).filter(Organiser.id == dest.organiser_id).first() if dest.organiser_id else None
        
        dispatch_list = []
        for d in dest_dispatches:
            conf_info = conf_by_dispatch.get(d.id, {})
            c_status = conf_info.get("status") if isinstance(conf_info, dict) else conf_info
            c_date = conf_info.get("date") if isinstance(conf_info, dict) else None
            c_by = conf_info.get("by") if isinstance(conf_info, dict) else None
            dispatch_list.append(DestinationDispatchItem(
                dispatch_id=d.id,
                dispatch_code=d.dispatch_code,
                dispatch_date=d.dispatch_date,
                items=items_by_dispatch.get(d.id, {}),
                awb_number=d.awb_number,
                courier_partner=d.courier_partner,
                courier_status=d.courier_status,
                confirmation_status=c_status,
                confirmation_date=c_date,
                confirmed_by_name=c_by,
                box_count=d.box_count,
                actual_delivery_date=d.actual_delivery_date,
                notes=d.notes
            ))
            
        latest_conf = conf_by_dispatch.get(latest_dispatch.id, {}) if latest_dispatch else {}
        latest_c_status = latest_conf.get("status") if isinstance(latest_conf, dict) else latest_conf
        latest_c_date = latest_conf.get("date") if isinstance(latest_conf, dict) else None
        latest_c_by = latest_conf.get("by") if isinstance(latest_conf, dict) else None

        dest_summaries.append(DestinationStatusSummary(
            destination_id=dest.id,
            destination_name=dest.destination_name,
            event_date=dest.event_date,
            organiser_name=organiser.organiser_name if organiser else None,
            contact_person=dest.contact_person,
            mobile=dest.mobile,
            email=dest.email or (organiser.email if organiser else None),
            address_line1=dest.address_line1,
            district=dest.district,
            city=dest.city,
            state=dest.state,
            pin=dest.pin,
            required=required_qty,
            sent=sent_qty,
            remaining=remaining_qty,
            shipment_count=len(dest_dispatches),
            latest_dispatch_date=latest_dispatch.dispatch_date if latest_dispatch else None,
            latest_awb=latest_dispatch.awb_number if latest_dispatch else None,
            latest_courier=latest_dispatch.courier_partner if latest_dispatch else None,
            latest_delivery_date=latest_dispatch.actual_delivery_date if latest_dispatch else None,
            box_count=latest_dispatch.box_count if latest_dispatch else None,
            courier_status=latest_dispatch.courier_status if latest_dispatch else None,
            confirmation_status=latest_c_status,
            confirmation_date=latest_c_date,
            confirmed_by_name=latest_c_by,
            fulfillment=fulfillment,
            dispatches=dispatch_list
        ))
        
    stock_groups = db.query(StockTransaction.collateral_code, func.sum(StockTransaction.quantity)).filter(StockTransaction.event_id == id).group_by(StockTransaction.collateral_code).all()
    stock_summary = {code: qty for code, qty in stock_groups}
    
    total_dest = len(destinations)
    dest_not_dispatched = sum(1 for d in dest_summaries if d.fulfillment == "NOT_STARTED")
    dest_partial = sum(1 for d in dest_summaries if d.fulfillment == "PARTIAL")
    dest_complete = sum(1 for d in dest_summaries if d.fulfillment in ["COMPLETE", "OVER_DISPATCHED", "DISPATCHED"])
    
    total_shipments = len(all_dispatches)
    shipments_in_transit = sum(1 for d in all_dispatches if d.courier_status in ["SHIPPED", "IN_TRANSIT"])
    confirmations_pending = sum(
        1 for d in all_dispatches 
        if d.courier_status == "DELIVERED" and (
            (conf_by_dispatch.get(d.id, {}).get("status") if isinstance(conf_by_dispatch.get(d.id), dict) else conf_by_dispatch.get(d.id)) in [None, "PENDING"]
        )
    )

    return EventOperationalSummary(
        event_id=event.id,
        event_name=event.name,
        event_code=event.event_code,
        city=event.city,
        state=event.state,
        start_date=event.start_date,
        end_date=event.end_date,
        delivery_deadline=event.delivery_deadline,
        status=event.status,
        participant_count=participant_count,
        destination_summary=dest_summaries,
        stock_summary=stock_summary,
        total_destinations=total_dest,
        destinations_not_dispatched=dest_not_dispatched,
        destinations_partial=dest_partial,
        destinations_complete=dest_complete,
        total_shipments=total_shipments,
        shipments_in_transit=shipments_in_transit,
        confirmations_pending=confirmations_pending
    )

@router.get("/{event_id}/destinations/{destination_id}/status", response_model=DestinationStatusSummary)
def get_destination_status(event_id: int, destination_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    dest = db.query(EventDestination).filter(EventDestination.id == destination_id, EventDestination.event_id == event_id).first()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")
        
    dest_dispatches = db.query(Dispatch).filter(Dispatch.destination_id == destination_id).all()
    dispatch_ids = [d.id for d in dest_dispatches]
    
    dispatch_items = db.query(DispatchItem).filter(DispatchItem.dispatch_id.in_(dispatch_ids)).all() if dispatch_ids else []
    confirmations = db.query(DeliveryConfirmation).filter(DeliveryConfirmation.dispatch_id.in_(dispatch_ids)).all() if dispatch_ids else []
    
    items_by_dispatch = {}
    for item in dispatch_items:
        items_by_dispatch.setdefault(item.dispatch_id, {})[item.collateral_code] = item.quantity
        
    conf_by_dispatch = {
        c.dispatch_id: {
            "status": c.confirmation_status,
            "date": str(c.confirmation_date).split()[0] if c.confirmation_date else None,
            "by": c.confirmed_by_name
        } for c in confirmations
    }
    
    required_qty = dest.required_quantities or {}
    sent_qty = {}
    for d in dest_dispatches:
        d_items = items_by_dispatch.get(d.id, {})
        for code, qty in d_items.items():
            sent_qty[code] = sent_qty.get(code, 0) + qty
            
    remaining_qty = {}
    for code, req in required_qty.items():
        sent = sent_qty.get(code, 0)
        if req - sent > 0:
            remaining_qty[code] = req - sent
            
    fulfillment = "NOT_STARTED"
    if not required_qty:
        if dest_dispatches:
            fulfillment = "DISPATCHED"
    else:
        if not dest_dispatches:
            fulfillment = "NOT_STARTED"
        else:
            is_complete = True
            is_over = False
            for code, req in required_qty.items():
                sent = sent_qty.get(code, 0)
                if sent < req:
                    is_complete = False
                if sent > req:
                    is_over = True
            
            if is_complete:
                fulfillment = "OVER_DISPATCHED" if is_over else "COMPLETE"
            else:
                fulfillment = "PARTIAL"
                
    latest_dispatch = max(dest_dispatches, key=lambda x: x.dispatch_date or date.min) if dest_dispatches else None
    
    organiser = db.query(Organiser).filter(Organiser.id == dest.organiser_id).first() if dest.organiser_id else None
    
    dispatch_list = []
    for d in dest_dispatches:
        conf_info = conf_by_dispatch.get(d.id, {})
        c_status = conf_info.get("status") if isinstance(conf_info, dict) else conf_info
        c_date = conf_info.get("date") if isinstance(conf_info, dict) else None
        c_by = conf_info.get("by") if isinstance(conf_info, dict) else None
        dispatch_list.append(DestinationDispatchItem(
            dispatch_id=d.id,
            dispatch_code=d.dispatch_code,
            dispatch_date=d.dispatch_date,
            items=items_by_dispatch.get(d.id, {}),
            awb_number=d.awb_number,
            courier_partner=d.courier_partner,
            courier_status=d.courier_status,
            confirmation_status=c_status,
            confirmation_date=c_date,
            confirmed_by_name=c_by
        ))
        
    latest_conf = conf_by_dispatch.get(latest_dispatch.id, {}) if latest_dispatch else {}
    latest_c_status = latest_conf.get("status") if isinstance(latest_conf, dict) else latest_conf
    latest_c_date = latest_conf.get("date") if isinstance(latest_conf, dict) else None
    latest_c_by = latest_conf.get("by") if isinstance(latest_conf, dict) else None

    return DestinationStatusSummary(
        destination_id=dest.id,
        destination_name=dest.destination_name,
        event_date=dest.event_date,
        organiser_name=organiser.organiser_name if organiser else None,
        contact_person=dest.contact_person,
        mobile=dest.mobile,
        address_line1=dest.address_line1,
        district=dest.district,
        city=dest.city,
        state=dest.state,
        pin=dest.pin,
        required=required_qty,
        sent=sent_qty,
        remaining=remaining_qty,
        shipment_count=len(dest_dispatches),
        latest_dispatch_date=latest_dispatch.dispatch_date if latest_dispatch else None,
        latest_awb=latest_dispatch.awb_number if latest_dispatch else None,
        courier_status=latest_dispatch.courier_status if latest_dispatch else None,
        confirmation_status=latest_c_status,
        confirmation_date=latest_c_date,
        confirmed_by_name=latest_c_by,
        fulfillment=fulfillment,
        dispatches=dispatch_list
    )

@router.get("/", response_model=PaginatedResponse)
def list_events(status: Optional[str] = None, page: int = 1, page_size: int = 50, db: Session = Depends(get_db)):
    query = db.query(Event)
    if status:
        query = query.filter(Event.status == status)
    
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return PaginatedResponse(
        items=[EventResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )

@router.get("/{id}", response_model=EventResponse)
def get_event(id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@router.post("/", response_model=EventResponse)
def create_event(event_in: EventCreate, db: Session = Depends(get_db)):
    if not event_in.event_code:
        event_in.event_code = generate_event_code()
        
    new_event = Event(**event_in.model_dump())
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    create_audit_log(db, "Event", new_event.id, "CREATE", f"Created event {new_event.event_code}")
    return new_event

@router.put("/{id}", response_model=EventResponse)
def update_event(id: int, event_in: EventUpdate, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    old_values = {}
    new_values = {}
    
    for k, v in event_in.model_dump(exclude_unset=True).items():
        old_val = getattr(event, k)
        if isinstance(old_val, date):
            old_val = old_val.isoformat()
            
        old_values[k] = old_val
        setattr(event, k, v)
        
        new_val = v
        if isinstance(new_val, date):
            new_val = new_val.isoformat()
        new_values[k] = new_val
        
    db.commit()
    db.refresh(event)
    
    import json
    create_audit_log(db, "Event", event.id, "UPDATE", "Updated event dates/info", json.dumps(old_values), json.dumps(new_values))
    return event

@router.delete("/{id}")
def delete_event(id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.status = "CANCELLED"
    db.commit()
    create_audit_log(db, "Event", event.id, "CANCEL", "Marked event as cancelled")
    return {"detail": "Event cancelled"}
