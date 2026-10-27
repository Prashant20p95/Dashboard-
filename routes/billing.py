from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import PrintingInvoice, CourierInvoice
from schemas import (
    PrintingInvoiceCreate, PrintingInvoiceUpdate, PrintingInvoiceResponse,
    CourierInvoiceCreate, CourierInvoiceUpdate, CourierInvoiceResponse
)

router = APIRouter()

@router.post("/printing-invoices", response_model=PrintingInvoiceResponse)
def create_printing_invoice(invoice_in: PrintingInvoiceCreate, db: Session = Depends(get_db)):
    invoice = PrintingInvoice(**invoice_in.model_dump())
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice

@router.get("/printing-invoices", response_model=List[PrintingInvoiceResponse])
def list_printing_invoices(
    event_id: Optional[int] = None,
    payment_status: Optional[str] = None,
    vendor_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(PrintingInvoice)
    if event_id: q = q.filter(PrintingInvoice.event_id == event_id)
    if payment_status: q = q.filter(PrintingInvoice.payment_status == payment_status)
    if vendor_name: q = q.filter(PrintingInvoice.vendor_name == vendor_name)
    return q.all()

@router.get("/printing-invoices/{invoice_id}", response_model=PrintingInvoiceResponse)
def get_printing_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(PrintingInvoice).filter(PrintingInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

@router.put("/printing-invoices/{invoice_id}", response_model=PrintingInvoiceResponse)
def update_printing_invoice(invoice_id: int, invoice_update: PrintingInvoiceUpdate, db: Session = Depends(get_db)):
    invoice = db.query(PrintingInvoice).filter(PrintingInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    for k, v in invoice_update.model_dump(exclude_unset=True).items():
        setattr(invoice, k, v)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/courier-invoices", response_model=CourierInvoiceResponse)
def create_courier_invoice(invoice_in: CourierInvoiceCreate, db: Session = Depends(get_db)):
    invoice = CourierInvoice(**invoice_in.model_dump())
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice

@router.get("/courier-invoices", response_model=List[CourierInvoiceResponse])
def list_courier_invoices(
    event_id: Optional[int] = None,
    payment_status: Optional[str] = None,
    courier_partner: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(CourierInvoice)
    if event_id: q = q.filter(CourierInvoice.event_id == event_id)
    if payment_status: q = q.filter(CourierInvoice.payment_status == payment_status)
    if courier_partner: q = q.filter(CourierInvoice.courier_partner == courier_partner)
    return q.all()

@router.get("/courier-invoices/{invoice_id}", response_model=CourierInvoiceResponse)
def get_courier_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(CourierInvoice).filter(CourierInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

@router.put("/courier-invoices/{invoice_id}", response_model=CourierInvoiceResponse)
def update_courier_invoice(invoice_id: int, invoice_update: CourierInvoiceUpdate, db: Session = Depends(get_db)):
    invoice = db.query(CourierInvoice).filter(CourierInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    for k, v in invoice_update.model_dump(exclude_unset=True).items():
        setattr(invoice, k, v)
    db.commit()
    db.refresh(invoice)
    return invoice

@router.get("/summary")
def billing_summary(event_id: int, db: Session = Depends(get_db)):
    print_stats = db.query(func.sum(PrintingInvoice.total_amount), func.count(PrintingInvoice.id)).filter(PrintingInvoice.event_id == event_id).first()
    cour_stats = db.query(func.sum(CourierInvoice.total_amount), func.count(CourierInvoice.id)).filter(CourierInvoice.event_id == event_id).first()
    
    paid_print = db.query(func.sum(PrintingInvoice.total_amount)).filter(PrintingInvoice.event_id == event_id, PrintingInvoice.payment_status == 'PAID').scalar() or 0
    paid_cour = db.query(func.sum(CourierInvoice.total_amount)).filter(CourierInvoice.event_id == event_id, CourierInvoice.payment_status == 'PAID').scalar() or 0
    
    total_print = print_stats[0] or 0
    total_cour = cour_stats[0] or 0
    total = total_print + total_cour
    paid = paid_print + paid_cour
    
    return {
        "total_printing_bills": print_stats[1] or 0,
        "total_courier_bills": cour_stats[1] or 0,
        "total_amount": total,
        "paid_amount": paid,
        "pending_amount": total - paid
    }
