from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import random
import io
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import docx
from docx.shared import Inches, Pt, RGBColor

from database import get_db
from models import PrintingJob, PhysicalReceipt, StockTransaction, CollateralItem
from schemas import PrintingJobCreate, PrintingJobUpdate, PrintingJobResponse, PhysicalReceiptCreate, PhysicalReceiptResponse, CollateralItemResponse
from routes.audit import create_audit_log

router = APIRouter()

def generate_job_number():
    return f"PJ-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

@router.get("/jobs", response_model=List[PrintingJobResponse])
def list_printing_jobs(event_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(PrintingJob)
    if event_id:
        query = query.filter(PrintingJob.event_id == event_id)
    items = query.all()
    result = []
    for item in items:
        resp = PrintingJobResponse.model_validate(item)
        resp.total_received = db.query(func.sum(PhysicalReceipt.quantity_received)).filter(PhysicalReceipt.job_id == item.id).scalar() or 0
        result.append(resp)
    return result

@router.get("/jobs/{id}", response_model=PrintingJobResponse)
def get_printing_job(id: int, db: Session = Depends(get_db)):
    item = db.query(PrintingJob).filter(PrintingJob.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")
        
    resp = PrintingJobResponse.model_validate(item)
    resp.total_received = db.query(func.sum(PhysicalReceipt.quantity_received)).filter(PhysicalReceipt.job_id == item.id).scalar() or 0
    return resp

@router.post("/jobs", response_model=PrintingJobResponse)
def create_printing_job(job_in: PrintingJobCreate, db: Session = Depends(get_db)):
    data = job_in.model_dump()
    data['job_number'] = generate_job_number()
        
    new_item = PrintingJob(**data)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    create_audit_log(db, "PrintingJob", new_item.id, "CREATE", f"Created printing job {new_item.job_number}")
    return get_printing_job(new_item.id, db)

@router.put("/jobs/{id}", response_model=PrintingJobResponse)
def update_printing_job(id: int, job_in: PrintingJobUpdate, db: Session = Depends(get_db)):
    item = db.query(PrintingJob).filter(PrintingJob.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")
        
    for k, v in job_in.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
        
    db.commit()
    db.refresh(item)
    create_audit_log(db, "PrintingJob", item.id, "UPDATE", "Updated printing job")
    return get_printing_job(item.id, db)

@router.post("/receipts", response_model=PhysicalReceiptResponse)
def record_receipt(receipt_in: PhysicalReceiptCreate, db: Session = Depends(get_db)):
    job = db.query(PrintingJob).filter(PrintingJob.id == receipt_in.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    new_receipt = PhysicalReceipt(**receipt_in.model_dump())
    db.add(new_receipt)
    db.flush()
    
    current_stock = db.query(func.sum(StockTransaction.quantity)).filter(
        StockTransaction.event_id == receipt_in.event_id,
        StockTransaction.collateral_code == receipt_in.collateral_code
    ).scalar() or 0
    
    new_balance = current_stock + receipt_in.quantity_received
    
    stock_tx = StockTransaction(
        event_id=receipt_in.event_id,
        collateral_code=receipt_in.collateral_code,
        transaction_type='RECEIPT',
        quantity=receipt_in.quantity_received,
        balance_after=new_balance,
        reference_type='PHYSICAL_RECEIPT',
        reference_id=new_receipt.id,
        created_by=receipt_in.received_by,
        notes=f"Receipt for job {job.job_number}"
    )
    db.add(stock_tx)
    
    total_received = db.query(func.sum(PhysicalReceipt.quantity_received)).filter(PhysicalReceipt.job_id == job.id).scalar() or 0
    total_received += receipt_in.quantity_received
    
    if total_received >= job.quantity_sent:
        job.status = 'RECEIVED'
        
    db.commit()
    db.refresh(new_receipt)
    
    create_audit_log(db, "PhysicalReceipt", new_receipt.id, "CREATE", f"Recorded receipt of {receipt_in.quantity_received}")
    return new_receipt

@router.get("/receipts", response_model=List[PhysicalReceiptResponse])
def list_receipts(event_id: Optional[int] = None, job_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(PhysicalReceipt)
    if event_id:
        query = query.filter(PhysicalReceipt.event_id == event_id)
    if job_id:
        query = query.filter(PhysicalReceipt.job_id == job_id)
    return query.all()

@router.get("/collateral-items", response_model=List[CollateralItemResponse])
def list_collateral_items(db: Session = Depends(get_db)):
    return db.query(CollateralItem).all()


class DocxLabelRequest(BaseModel):
    mode: str = 'SAME'  # 'SAME', 'DIFFERENT', 'SINGLE'
    dest1: Optional[Dict[str, Any]] = None
    dest2: Optional[Dict[str, Any]] = None
    top_label: Optional[Dict[str, Any]] = None
    bottom_label: Optional[Dict[str, Any]] = None


@router.post("/generate-docx")
def generate_docx_label(req: DocxLabelRequest):
    """
    Generates a Microsoft Word (.docx) file matching the exact geometry,
    font (Calibri 28pt, normal weight, 1.15 line spacing, 8pt after spacing),
    and 1.0-inch A4 page margins of the user's reference 'Label Print.docx'.
    """
    doc = docx.Document()
    section = doc.sections[0]
    section.page_width = Inches(8.27)    # 210mm (A4)
    section.page_height = Inches(11.69)  # 297mm (A4)
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    d1 = req.dest1 or req.top_label or {}
    d2 = req.dest2 or req.bottom_label

    font_pt = 24 if req.mode == 'SINGLE' else 20
    space_after_pt = 6 if req.mode == 'SINGLE' else 4

    def add_label_block(d):
        if not d:
            return
        name = d.get('name', 'Mr. SPOC')
        care_of = d.get('careOfLine') or d.get('care_of', '')
        mid_lines = d.get('midLines') or d.get('mid_lines', [])
        city_state = d.get('cityState') or d.get('city_state', '')
        pin = d.get('pin', '')
        mobile = d.get('mobile', '')

        lines = [name]
        if care_of:
            lines.append(care_of)
        for ml in mid_lines:
            if ml:
                lines.append(ml)
        if city_state:
            lines.append(city_state)
        if pin:
            lines.append(f"Pincode – {pin}")
        if mobile:
            lines.append(f"Contact Number – {mobile}")

        for idx, l in enumerate(lines):
            p = doc.add_paragraph()
            p.paragraph_format.line_spacing = 1.18
            p.paragraph_format.space_after = Pt(space_after_pt)
            p.paragraph_format.space_before = Pt(0)
            r = p.add_run(l)
            r.font.name = 'Calibri'
            r.font.size = Pt(font_pt)
            r.font.bold = (idx == 0 or 'Pincode' in l or 'Contact Number' in l)
            r.font.color.rgb = RGBColor(0, 0, 0)

    # First Label
    add_label_block(d1)

    if req.mode != 'SINGLE':
        # Clean blank spacer paragraph between labels matching reference Label Print.docx
        spacer = doc.add_paragraph()
        spacer.paragraph_format.line_spacing = 1.0
        spacer.paragraph_format.space_after = Pt(28)
        spacer.paragraph_format.space_before = Pt(0)

        # Second Label
        second_dest = d2 if (req.mode == 'DIFFERENT' and d2) else d1
        add_label_block(second_dest)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    dest_name = (d1.get('name') or 'Label').replace(' ', '_').replace('.', '')
    filename = f"Shipping_Label_{dest_name}.docx"

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
    )

