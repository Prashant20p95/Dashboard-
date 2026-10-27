from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from database import get_db
from models import Event, Participant, EventDestination, Dispatch, DispatchItem, StockTransaction, DeliveryConfirmation, PrintingJob, PhysicalReceipt, PrintingInvoice, CourierInvoice, Organiser
from schemas import DashboardResponse, EventDashboardSummary, ActionRequiredItem

router = APIRouter()

@router.get("/", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)):
    from datetime import date, timedelta
    today = date.today()
    
    active_events_query = db.query(Event).filter(Event.status.in_(["ACTIVE", "IN_PROGRESS"])).all()
    
    active_events = []
    action_required = []
    
    total_events = db.query(func.count(Event.id)).scalar() or 0
    total_participants = db.query(func.count(Participant.id)).scalar() or 0
    total_organisers = db.query(func.count(Organiser.id)).scalar() or 0
    
    # Global KPIs
    total_dispatches = db.query(func.count(Dispatch.id)).scalar() or 0
    dispatches_in_transit = db.query(func.count(Dispatch.id)).filter(Dispatch.courier_status.in_(["IN_TRANSIT", "SHIPPED"])).scalar() or 0
    
    delivered_awaiting_confirmation = db.query(func.count(Dispatch.id)).outerjoin(DeliveryConfirmation).filter(
        Dispatch.courier_status == 'DELIVERED',
        (DeliveryConfirmation.id == None) | (DeliveryConfirmation.confirmation_status == 'PENDING')
    ).scalar() or 0
    
    # For RTO/exceptions globally
    global_rto = db.query(func.count(Dispatch.id)).filter(Dispatch.courier_status.in_(["RTO", "EXCEPTION"])).scalar() or 0
    if global_rto > 0:
        action_required.append(ActionRequiredItem(severity="critical", message=f"{global_rto} courier RTO/exceptions", count=global_rto))
        
    global_destinations_requiring_dispatch = 0
    global_upcoming_deadlines = 0
    
    for e in active_events_query:
        participant_count = db.query(func.count(Participant.id)).filter(Participant.event_id == e.id).scalar() or 0
        cards_printed = db.query(func.sum(PrintingJob.quantity_sent)).filter(PrintingJob.event_id == e.id).scalar() or 0
        cards_received = db.query(func.sum(PhysicalReceipt.quantity_received)).filter(PhysicalReceipt.event_id == e.id).scalar() or 0
        
        destinations = db.query(EventDestination).filter(EventDestination.event_id == e.id).all()
        destination_count = len(destinations)
        
        dispatched_quantity = db.query(func.sum(DispatchItem.quantity)).join(Dispatch).filter(Dispatch.event_id == e.id).scalar() or 0
        
        remaining_stock = {}
        stock_groups = db.query(StockTransaction.collateral_code, func.sum(StockTransaction.quantity)).filter(StockTransaction.event_id == e.id).group_by(StockTransaction.collateral_code).all()
        for code, qty in stock_groups:
            remaining_stock[code] = qty or 0
            
        deliveries_complete = db.query(func.count(Dispatch.id)).filter(Dispatch.event_id == e.id, Dispatch.courier_status == 'DELIVERED').scalar() or 0
        
        # confirmations pending: DELIVERED but no delivery_confirmation or confirmation_status='PENDING'
        confirmations_pending_q = db.query(func.count(Dispatch.id)).outerjoin(DeliveryConfirmation).filter(
            Dispatch.event_id == e.id, 
            Dispatch.courier_status == 'DELIVERED',
            (DeliveryConfirmation.id == None) | (DeliveryConfirmation.confirmation_status == 'PENDING')
        ).scalar() or 0
        
        printing_bills_pending = db.query(func.count(PrintingInvoice.id)).filter(PrintingInvoice.event_id == e.id, PrintingInvoice.payment_status == 'PENDING').scalar() or 0
        courier_bills_pending = db.query(func.count(CourierInvoice.id)).filter(CourierInvoice.event_id == e.id, CourierInvoice.payment_status == 'PENDING').scalar() or 0
        
        # compute destination fulfillment for this event
        event_dispatches = db.query(Dispatch).filter(Dispatch.event_id == e.id).all()
        total_shipments = len(event_dispatches)
        
        dispatch_items = db.query(DispatchItem).join(Dispatch).filter(Dispatch.event_id == e.id).all()
        items_by_dispatch = {}
        for item in dispatch_items:
            items_by_dispatch.setdefault(item.dispatch_id, {})[item.collateral_code] = item.quantity
            
        dispatch_by_dest = {}
        for d in event_dispatches:
            dispatch_by_dest.setdefault(d.destination_id, []).append(d)
            
        dest_fulfilled = 0
        dest_partial = 0
        dest_pending = 0
        
        for dest in destinations:
            req = dest.required_quantities or {}
            d_list = dispatch_by_dest.get(dest.id, [])
            
            if not req:
                if d_list:
                    dest_fulfilled += 1
                else:
                    dest_pending += 1
                continue
                
            if not d_list:
                dest_pending += 1
                continue
                
            sent_qty = {}
            for d in d_list:
                d_items = items_by_dispatch.get(d.id, {})
                for code, qty in d_items.items():
                    sent_qty[code] = sent_qty.get(code, 0) + qty
                    
            is_complete = True
            for code, rqty in req.items():
                if sent_qty.get(code, 0) < rqty:
                    is_complete = False
                    break
                    
            if is_complete:
                dest_fulfilled += 1
            else:
                dest_partial += 1
                
        global_destinations_requiring_dispatch += dest_pending
        
        if e.delivery_deadline:
            if 0 <= (e.delivery_deadline - today).days <= 7:
                global_upcoming_deadlines += 1
            if e.delivery_deadline < today and dest_pending > 0:
                action_required.append(ActionRequiredItem(
                    severity="critical", 
                    message=f"{dest_pending} destinations past deadline without dispatch for {e.name}", 
                    count=dest_pending
                ))
                
        if dest_partial > 0:
            action_required.append(ActionRequiredItem(
                severity="warning",
                message=f"{dest_partial} destinations with partial fulfillment for {e.name}",
                count=dest_partial
            ))
        
        active_events.append(EventDashboardSummary(
            event_id=e.id,
            event_name=e.name,
            event_code=e.event_code,
            city=e.city,
            state=e.state,
            start_date=e.start_date,
            delivery_deadline=e.delivery_deadline,
            status=e.status,
            participant_count=participant_count,
            cards_printed=cards_printed,
            cards_received=cards_received,
            destination_count=destination_count,
            destinations_fulfilled=dest_fulfilled,
            destinations_partial=dest_partial,
            destinations_pending=dest_pending,
            total_shipments=total_shipments,
            dispatched_quantity=dispatched_quantity,
            remaining_stock=remaining_stock,
            deliveries_complete=deliveries_complete,
            confirmations_pending=confirmations_pending_q,
            printing_bills_pending=printing_bills_pending,
            courier_bills_pending=courier_bills_pending
        ))
        
        if confirmations_pending_q > 0:
            action_required.append(ActionRequiredItem(severity="warning", message=f"{confirmations_pending_q} deliveries awaiting confirmation for {e.name}", count=confirmations_pending_q))
            
    return DashboardResponse(
        active_events=active_events,
        action_required=action_required,
        total_events=total_events,
        total_participants=total_participants,
        total_organisers=total_organisers,
        total_dispatches=total_dispatches,
        dispatches_in_transit=dispatches_in_transit,
        delivered_awaiting_confirmation=delivered_awaiting_confirmation,
        destinations_requiring_dispatch=global_destinations_requiring_dispatch,
        upcoming_deadlines=global_upcoming_deadlines
    )
