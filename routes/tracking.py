from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Dispatch, DeliveryConfirmation, Event
from schemas import (
    DeliveryConfirmationCreate, DeliveryConfirmationUpdate, DeliveryConfirmationResponse,
    DispatchResponse
)

router = APIRouter()

@router.put("/{dispatch_id}/courier-status", response_model=DispatchResponse)
def update_courier_status(dispatch_id: int, courier_status: str, db: Session = Depends(get_db)):
    dispatch = db.query(Dispatch).filter(Dispatch.id == dispatch_id).first()
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    dispatch.courier_status = courier_status
    if courier_status == "DELIVERED":
        dispatch.actual_delivery_date = datetime.now().date()
    db.commit()
    db.refresh(dispatch)
    return dispatch

@router.post("/{dispatch_id}/confirmation", response_model=DeliveryConfirmationResponse)
def create_delivery_confirmation(dispatch_id: int, conf_in: DeliveryConfirmationCreate, db: Session = Depends(get_db)):
    dispatch = db.query(Dispatch).filter(Dispatch.id == dispatch_id).first()
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")
        
    existing = db.query(DeliveryConfirmation).filter(DeliveryConfirmation.dispatch_id == dispatch_id).first()
    if existing:
        existing.confirmation_status = conf_in.confirmation_status
        if conf_in.confirmed_by_name: existing.confirmed_by_name = conf_in.confirmed_by_name
        if conf_in.confirmed_by_user: existing.confirmed_by_user = conf_in.confirmed_by_user
        if conf_in.confirmation_method: existing.confirmation_method = conf_in.confirmation_method
        existing.confirmation_date = conf_in.confirmation_date or datetime.now()
        if conf_in.issue_description is not None: existing.issue_description = conf_in.issue_description
        if conf_in.notes is not None: existing.notes = conf_in.notes
        
        if conf_in.confirmation_status == "CONFIRMED" and dispatch.courier_status != "DELIVERED":
            dispatch.courier_status = "DELIVERED"
            dispatch.actual_delivery_date = datetime.now().date()
            
        db.commit()
        db.refresh(existing)
        return existing
        
    conf = DeliveryConfirmation(
        dispatch_id=dispatch_id,
        confirmation_status=conf_in.confirmation_status,
        confirmed_by_name=conf_in.confirmed_by_name,
        confirmed_by_user=conf_in.confirmed_by_user,
        confirmation_method=conf_in.confirmation_method,
        confirmation_date=conf_in.confirmation_date or datetime.now(),
        issue_description=conf_in.issue_description,
        notes=conf_in.notes
    )
    db.add(conf)
    if conf_in.confirmation_status == "CONFIRMED" and dispatch.courier_status != "DELIVERED":
        dispatch.courier_status = "DELIVERED"
        dispatch.actual_delivery_date = datetime.now().date()
    db.commit()
    db.refresh(conf)
    return conf

@router.post("/destinations/{destination_id}/confirm", response_model=DeliveryConfirmationResponse)
def confirm_destination_delivery(destination_id: int, conf_in: DeliveryConfirmationCreate, db: Session = Depends(get_db)):
    from models import EventDestination, DispatchItem
    import random
    latest_dispatch = db.query(Dispatch).filter(Dispatch.destination_id == destination_id).order_by(Dispatch.id.desc()).first()
    if not latest_dispatch:
        dest = db.query(EventDestination).filter(EventDestination.id == destination_id).first()
        if not dest:
            raise HTTPException(status_code=404, detail="Destination station not found")
            
        date_str = datetime.now().strftime("%Y%m%d")
        rnd = random.randint(1000, 9999)
        dsp_code = f"DSP-DIR-{date_str}-{rnd}"
        latest_dispatch = Dispatch(
            dispatch_code=dsp_code,
            event_id=dest.event_id,
            destination_id=dest.id,
            hist_organiser_name=dest.destination_name,
            hist_contact_person=dest.contact_person,
            hist_mobile=dest.mobile,
            hist_address_line1=dest.address_line1,
            hist_district=dest.district,
            hist_city=dest.city,
            hist_state=dest.state,
            hist_pin=dest.pin,
            dispatch_date=datetime.now().date(),
            courier_partner="Direct Handover / Special Express",
            awb_number=f"DIR-{date_str}-{rnd}",
            actual_delivery_date=datetime.now().date(),
            courier_status="DELIVERED",
            notes="Auto-generated on direct station receipt confirmation."
        )
        db.add(latest_dispatch)
        db.flush()
        
        # Add required quantities as items
        req = dest.required_quantities or {}
        for code, qty in req.items():
            db.add(DispatchItem(dispatch_id=latest_dispatch.id, collateral_code=code, quantity=qty))
        db.flush()
        
    return create_delivery_confirmation(latest_dispatch.id, conf_in, db)

@router.put("/confirmations/{conf_id}", response_model=DeliveryConfirmationResponse)
def update_delivery_confirmation(conf_id: int, conf_update: DeliveryConfirmationUpdate, db: Session = Depends(get_db)):
    conf = db.query(DeliveryConfirmation).filter(DeliveryConfirmation.id == conf_id).first()
    if not conf:
        raise HTTPException(status_code=404, detail="Confirmation not found")
        
    if conf_update.confirmation_status: conf.confirmation_status = conf_update.confirmation_status
    if conf_update.confirmed_by_name: conf.confirmed_by_name = conf_update.confirmed_by_name
    if conf_update.confirmed_by_user: conf.confirmed_by_user = conf_update.confirmed_by_user
    if conf_update.confirmation_method: conf.confirmation_method = conf_update.confirmation_method
    if conf_update.confirmation_date: conf.confirmation_date = conf_update.confirmation_date
    if conf_update.issue_description: conf.issue_description = conf_update.issue_description
    if conf_update.notes: conf.notes = conf_update.notes
    
    db.commit()
    db.refresh(conf)
    return conf

@router.get("/pending-confirmation")
def list_pending_confirmations(event_id: int, db: Session = Depends(get_db)):
    q = db.query(Dispatch).outerjoin(DeliveryConfirmation).filter(
        Dispatch.event_id == event_id,
        Dispatch.courier_status == "DELIVERED"
    ).filter(
        (DeliveryConfirmation.id == None) | (DeliveryConfirmation.confirmation_status == "PENDING")
    )
    return [DispatchResponse.model_validate(d) for d in q.all()]

@router.get("/summary")
def tracking_summary(event_id: int, db: Session = Depends(get_db)):
    total = db.query(Dispatch).filter(Dispatch.event_id == event_id).count()
    status_counts = db.query(Dispatch.courier_status, func.count(Dispatch.id)).filter(Dispatch.event_id == event_id).group_by(Dispatch.courier_status).all()
    
    conf_counts = db.query(DeliveryConfirmation.confirmation_status, func.count(DeliveryConfirmation.id))\
        .join(Dispatch)\
        .filter(Dispatch.event_id == event_id)\
        .group_by(DeliveryConfirmation.confirmation_status).all()
        
    return {
        "total_dispatches": total,
        "courier_statuses": {s: c for s, c in status_counts},
        "confirmation_statuses": {s: c for s, c in conf_counts}
    }
