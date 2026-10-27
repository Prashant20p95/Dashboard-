from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from database import get_db
from models import StockTransaction, CollateralItem
from schemas import StockSummaryItem, StockTransactionResponse, StockAdjustRequest, PaginatedResponse
from routes.audit import create_audit_log

router = APIRouter()

@router.get("/", response_model=List[StockSummaryItem])
def get_stock_summary(event_id: int, db: Session = Depends(get_db)):
    items = db.query(CollateralItem).all()
    summary = []
    
    for item in items:
        txs = db.query(StockTransaction).filter(
            StockTransaction.event_id == event_id,
            StockTransaction.collateral_code == item.code
        ).all()
        
        total_received = sum(t.quantity for t in txs if t.transaction_type == 'RECEIPT')
        total_dispatched = abs(sum(t.quantity for t in txs if t.transaction_type == 'DISPATCH'))
        adjustments = sum(t.quantity for t in txs if t.transaction_type == 'ADJUSTMENT')
        current_stock = sum(t.quantity for t in txs)
        
        summary.append(StockSummaryItem(
            collateral_code=item.code,
            collateral_name=item.name,
            category=item.category,
            total_received=total_received,
            total_dispatched=total_dispatched,
            adjustments=adjustments,
            current_stock=current_stock
        ))
        
    return summary

@router.get("/transactions", response_model=PaginatedResponse)
def list_stock_transactions(event_id: int, collateral_code: str = None, page: int = 1, page_size: int = 50, db: Session = Depends(get_db)):
    query = db.query(StockTransaction).filter(StockTransaction.event_id == event_id)
    if collateral_code:
        query = query.filter(StockTransaction.collateral_code == collateral_code)
        
    query = query.order_by(StockTransaction.created_at.desc())
    
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return PaginatedResponse(
        items=[StockTransactionResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )

@router.post("/adjust", response_model=StockTransactionResponse)
def adjust_stock(adjust_in: StockAdjustRequest, db: Session = Depends(get_db)):
    if not adjust_in.notes:
        raise HTTPException(status_code=400, detail="Notes are mandatory for manual adjustments")
        
    current_stock = db.query(func.sum(StockTransaction.quantity)).filter(
        StockTransaction.event_id == adjust_in.event_id,
        StockTransaction.collateral_code == adjust_in.collateral_code
    ).scalar() or 0
    
    new_balance = current_stock + adjust_in.quantity
    
    tx = StockTransaction(
        event_id=adjust_in.event_id,
        collateral_code=adjust_in.collateral_code,
        transaction_type='ADJUSTMENT',
        quantity=adjust_in.quantity,
        balance_after=new_balance,
        reference_type='MANUAL_ADJUSTMENT',
        notes=adjust_in.notes
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    
    create_audit_log(db, "StockTransaction", tx.id, "ADJUST", f"Adjusted stock by {adjust_in.quantity}")
    return tx
