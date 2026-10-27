import os
import io
import re
import json
import sqlite3
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from database import get_db, DB_PATH
from models import (
    Event, EventDestination, Organiser, Dispatch,
    StockTransaction, DeliveryConfirmation, PrintingJob, Participant, AuditLog
)

router = APIRouter()

@router.get("/info")
def get_datastore_info(db: Session = Depends(get_db)):
    """Returns database status, persistence details, disk storage, and table counts."""
    db_size_bytes = 0
    if os.path.exists(DB_PATH):
        db_size_bytes = os.path.getsize(DB_PATH)
    
    # Active event
    active_event = db.query(Event).filter(Event.status == "ACTIVE").order_by(Event.id.desc()).first()
    event_id = active_event.id if active_event else 1
    
    # Counts
    station_count = db.query(EventDestination).filter(EventDestination.event_id == event_id).count()
    total_destinations = db.query(EventDestination).count()
    organisers_count = db.query(Organiser).count()
    dispatches_count = db.query(Dispatch).count()
    stock_count = db.query(StockTransaction).count()
    confirmations_count = db.query(DeliveryConfirmation).count()
    participants_count = db.query(Participant).count()
    jobs_count = db.query(PrintingJob).count()
    audit_count = db.query(AuditLog).count()

    return {
        "engine": "SQLite 3",
        "journal_mode": "WAL (Write-Ahead Logging)",
        "file_name": os.path.basename(DB_PATH),
        "file_path": DB_PATH,
        "file_size_mb": round(db_size_bytes / (1024 * 1024), 2),
        "status": "Healthy & Persistent",
        "last_synced": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "active_event": {
            "id": active_event.id if active_event else None,
            "name": active_event.name if active_event else "Operations Master 2026",
            "active_stations": station_count
        },
        "counts": {
            "active_stations": station_count,
            "total_destinations": total_destinations,
            "coordinators": organisers_count,
            "dispatches": dispatches_count,
            "call_confirmations": confirmations_count,
            "stock_transactions": stock_count,
            "print_jobs": jobs_count,
            "pass_holders": participants_count,
            "audit_logs": audit_count
        }
    }


@router.get("/backup-db")
def download_database_backup():
    """Download the raw SQLite database file directly as backup."""
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Database file not found")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return FileResponse(
        DB_PATH,
        filename=f"operations_backup_{timestamp}.db",
        media_type="application/octet-stream"
    )


@router.get("/template-excel")
def download_station_template():
    """Download a clean Excel template formatted for importing stations."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Stations Import"
    
    headers = [
        "Station Name", "State", "District", "Event Date (YYYY-MM-DD)",
        "Coordinator Name", "Mobile Number", "Delivery Address", "PIN Code",
        "Influencer Card Quota", "Special Delegate Card Quota", "VIP / Executive Card Quota", "Lanyards Quota"
    ]
    
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
    
    # Sample row
    sample = [
        "Kanpur North", "Uttar Pradesh", "Kanpur Nagar", "2026-10-15",
        "Rajesh Sharma", "9876543210", "Plot 42, Transport Nagar, Kanpur", "208001",
        2000, 500, 200, 2700
    ]
    for col_idx, val in enumerate(sample, 1):
        ws.cell(row=2, column=col_idx, value=val)
        
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)
        
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Stations_Import_Template.xlsx"}
    )


@router.post("/import-stations")
async def import_stations(
    file: UploadFile = File(...),
    event_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Import stations and coordinators from Excel or CSV directly into the datastore."""
    if not event_id:
        active_event = db.query(Event).filter(Event.status == "ACTIVE").order_by(Event.id.desc()).first()
        event_id = active_event.id if active_event else 1
        
    content = await file.read()
    filename = file.filename.lower()
    
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read spreadsheet file: {str(e)}")
        
    df = df.dropna(how="all")
    if df.empty:
        raise HTTPException(status_code=400, detail="Spreadsheet contains no data rows")

    # Normalize column names
    col_map = {}
    for c in df.columns:
        norm = str(c).strip().lower().replace("_", " ").replace("-", " ")
        if any(k in norm for k in ["station", "destination", "centre", "center"]):
            col_map["station"] = c
        elif any(k in norm for k in ["event date", "date"]):
            col_map["date"] = c
        elif any(k in norm for k in ["coordinator", "contact person", "contact"]):
            col_map["contact"] = c
        elif any(k in norm for k in ["mobile", "phone"]):
            col_map["mobile"] = c
        elif any(k in norm for k in ["address", "delivery address"]):
            col_map["address"] = c
        elif any(k in norm for k in ["district"]):
            col_map["district"] = c
        elif any(k in norm for k in ["state"]):
            col_map["state"] = c
        elif any(k in norm for k in ["pin", "zip"]):
            col_map["pin"] = c
        elif any(k in norm for k in ["influencer", "gold"]):
            col_map["gold"] = c
        elif any(k in norm for k in ["delegate", "silver"]):
            col_map["silver"] = c
        elif any(k in norm for k in ["vip", "team"]):
            col_map["vip"] = c
        elif any(k in norm for k in ["lanyard", "pouch"]):
            col_map["lanyard"] = c

    if "station" not in col_map:
        raise HTTPException(status_code=400, detail="Spreadsheet must have a column for 'Station Name'")

    inserted_count = 0
    updated_count = 0

    for _, row in df.iterrows():
        station_name = str(row[col_map["station"]]).strip()
        if not station_name or station_name.lower() == "nan":
            continue

        state_val = str(row[col_map["state"]]).strip() if "state" in col_map and pd.notna(row[col_map["state"]]) else ""
        dist_val = str(row[col_map["district"]]).strip() if "district" in col_map and pd.notna(row[col_map["district"]]) else ""
        contact_val = str(row[col_map["contact"]]).strip() if "contact" in col_map and pd.notna(row[col_map["contact"]]) else ""
        mobile_val = str(row[col_map["mobile"]]).strip() if "mobile" in col_map and pd.notna(row[col_map["mobile"]]) else ""
        addr_val = str(row[col_map["address"]]).strip() if "address" in col_map and pd.notna(row[col_map["address"]]) else ""
        pin_val = str(row[col_map["pin"]]).strip() if "pin" in col_map and pd.notna(row[col_map["pin"]]) else ""
        
        # Clean mobile
        if mobile_val.endswith(".0"):
            mobile_val = mobile_val[:-2]
        if pin_val.endswith(".0"):
            pin_val = pin_val[:-2]

        # Parse date
        evt_date = None
        if "date" in col_map and pd.notna(row[col_map["date"]]):
            try:
                parsed_dt = pd.to_datetime(row[col_map["date"]])
                evt_date = parsed_dt.date()
            except Exception:
                pass

        # Quotas directly from spreadsheet without any forced formulas
        inf_qty = int(row[col_map["gold"]]) if "gold" in col_map and pd.notna(row[col_map["gold"]]) and str(row[col_map["gold"]]).isdigit() else 0
        spec_qty = int(row[col_map["silver"]]) if "silver" in col_map and pd.notna(row[col_map["silver"]]) and str(row[col_map["silver"]]).isdigit() else 0
        vip_qty = int(row[col_map["vip"]]) if "vip" in col_map and pd.notna(row[col_map["vip"]]) and str(row[col_map["vip"]]).isdigit() else 0
        lanyard_qty = int(row[col_map["lanyard"]]) if "lanyard" in col_map and pd.notna(row[col_map["lanyard"]]) and str(row[col_map["lanyard"]]).isdigit() else (inf_qty + spec_qty + vip_qty)

        quotas = {
            "ITEM_PRIMARY": inf_qty,
            "ITEM_SECONDARY": spec_qty,
            "ITEM_VIP": vip_qty,
            "ITEM_ACCESSORY": lanyard_qty,
        }

        # Check existing destination
        dest = db.query(EventDestination).filter(
            EventDestination.event_id == event_id,
            EventDestination.destination_name == station_name
        ).first()

        if dest:
            # Update
            if evt_date:
                dest.event_date = evt_date
            if contact_val:
                dest.contact_person = contact_val
            if mobile_val:
                dest.mobile = mobile_val
            if addr_val:
                dest.address_line1 = addr_val
            if dist_val:
                dest.district = dist_val
            if state_val:
                dest.state = state_val
            if pin_val:
                dest.pin = pin_val
            dest.required_quantities_json = json.dumps(quotas)
            updated_count += 1
        else:
            # Create organiser if not exists
            code = f"ORG-{station_name[:4].upper()}-{len(mobile_val[-4:]) or '0000'}"
            org = db.query(Organiser).filter(Organiser.organiser_name == station_name).first()
            if not org:
                org = Organiser(
                    destination_code=f"DST-{int(datetime.now().timestamp())}-{inserted_count}",
                    organiser_name=station_name,
                    contact_person=contact_val,
                    mobile=mobile_val,
                    address_line1=addr_val,
                    district=dist_val,
                    state=state_val,
                    pin=pin_val
                )
                db.add(org)
                db.flush()

            dest = EventDestination(
                event_id=event_id,
                organiser_id=org.id,
                destination_name=station_name,
                event_date=evt_date or date(2026, 10, 15),
                contact_person=contact_val,
                mobile=mobile_val,
                address_line1=addr_val,
                district=dist_val,
                state=state_val,
                pin=pin_val,
                required_quantities_json=json.dumps(quotas)
            )
            db.add(dest)
            inserted_count += 1

    db.commit()
    return {
        "success": True,
        "message": f"Datastore updated: {inserted_count} stations added, {updated_count} stations updated.",
        "inserted": inserted_count,
        "updated": updated_count,
        "total_rows": len(df)
    }


@router.post("/import-users")
async def import_bulk_users(
    file: UploadFile = File(...),
    event_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Bulk import 100,000+ users / influencer cards from CSV or Excel directly into the datastore and influencer_attendees."""
    if not event_id:
        active_event = db.query(Event).filter(Event.status == "ACTIVE").order_by(Event.id.desc()).first()
        event_id = active_event.id if active_event else 17

    content = await file.read()
    filename = file.filename.lower()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content), dtype=str)
        else:
            df = pd.read_excel(io.BytesIO(content), dtype=str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read user spreadsheet: {str(e)}")

    df = df.dropna(how="all")
    if df.empty:
        raise HTTPException(status_code=400, detail="User spreadsheet contains no data rows")

    # Column mapping with word-boundary awareness
    col_map = {}
    for col in df.columns:
        c = str(col).strip().lower().replace("_", " ").replace("-", " ")
        if re.search(r'\b(name|inf name|full name|participant|user|guest|influencer)\b', c):
            col_map["name"] = col
        elif re.search(r'\b(otp|code|token|passcode|qr|serial)\b', c):
            col_map["code"] = col
        elif re.search(r'\b(category|cat|tier|grade)\b', c):
            col_map["card_type"] = col
        elif re.search(r'\b(event location|location|station|venue|city|district)\b', c):
            col_map["location"] = col
        elif re.search(r'\b(mobile|phone|contact)\b', c):
            col_map["mobile"] = col
        elif re.search(r'\b(email)\b', c):
            col_map["email"] = col
        elif re.search(r'\b(org|company|firm)\b', c):
            col_map["org"] = col

    name_col = col_map.get("name")
    code_col = col_map.get("code")
    card_col = col_map.get("card_type")
    loc_col = col_map.get("location")
    mobile_col = col_map.get("mobile")
    email_col = col_map.get("email")
    org_col = col_map.get("org")

    # Pre-fetch destinations for fast location matching
    destinations = db.query(EventDestination).all()
    dest_lookup = {}
    for d in destinations:
        clean_d = re.sub(r'\b(coordinator|hub|center|station)\b', '', d.destination_name.lower(), flags=re.I).strip()
        dest_lookup[clean_d] = d

    records = []
    inf_records = []
    matched_dest_ids = set()

    for idx, row in df.iterrows():
        full_name = str(row[name_col]).strip() if name_col and pd.notna(row[name_col]) else ""
        if not full_name or full_name.lower() in ["none", "null", "nan"]:
            continue

        raw_cat = str(row[card_col]).strip().upper() if card_col and pd.notna(row[card_col]) else "H"
        card_type = raw_cat if raw_cat in "ABCDEFGH" else "H"

        code = str(row[code_col]).strip().replace(".0", "") if code_col and pd.notna(row[code_col]) else ""
        if code.lower() in ["none", "null", "nan", "#n/a"]:
            code = ""

        raw_loc = str(row[loc_col]).strip() if loc_col and pd.notna(row[loc_col]) else ""
        mobile = str(row[mobile_col]).strip().replace(".0", "") if mobile_col and pd.notna(row[mobile_col]) else ""
        if mobile.lower() in ["none", "null", "nan"]:
            mobile = ""

        email = str(row[email_col]).strip() if email_col and pd.notna(row[email_col]) else ""
        org = str(row[org_col]).strip() if org_col and pd.notna(row[org_col]) else ""

        # Match location to destination
        dest_id = None
        matched_loc_name = raw_loc
        if raw_loc:
            clean_rloc = re.sub(r'\b(coordinator|hub|center|station)\b', '', raw_loc.lower(), flags=re.I).strip()
            for key, d in dest_lookup.items():
                if key in clean_rloc or clean_rloc in key:
                    dest_id = d.id
                    matched_loc_name = d.destination_name
                    matched_dest_ids.add(d.id)
                    break

        records.append((
            event_id, code or f"UU-{idx+1:06d}", full_name, mobile, email, org, card_type
        ))

        inf_records.append((
            dest_id, matched_loc_name or "Station", full_name, card_type, code, mobile, file.filename
        ))

    # High-speed SQLite bulk insert into participants
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT INTO participants (event_id, participant_code, full_name, mobile, email, organization, card_type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        records
    )

    # Insert into influencer_attendees
    # Clear prior records from the same file or for the matched destinations
    if matched_dest_ids:
        placeholders = ",".join("?" for _ in matched_dest_ids)
        cursor.execute(f"DELETE FROM influencer_attendees WHERE destination_id IN ({placeholders})", tuple(matched_dest_ids))
    cursor.execute("DELETE FROM influencer_attendees WHERE source_file = ?", (file.filename,))

    cursor.executemany(
        """
        INSERT INTO influencer_attendees (destination_id, location_name, name, category, otp, phone, source_file)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        inf_records
    )
    conn.commit()
    conn.close()

    total_now = db.query(Participant).count()

    return {
        "success": True,
        "message": f"Successfully loaded {len(inf_records):,} real attendees ({len(matched_dest_ids)} stations matched) from {file.filename} into Influencer Cards & Datastore!",
        "imported": len(inf_records),
        "matched_stations": len(matched_dest_ids),
        "total_users": total_now
    }


@router.post("/analyze-file")
async def analyze_uploaded_file(file: UploadFile = File(...)):
    """Inspects any uploaded Excel or CSV file, detects what category it belongs to, and maps columns."""
    content = await file.read()
    filename = file.filename.lower()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content), dtype=str, nrows=50)
        else:
            df = pd.read_excel(io.BytesIO(content), dtype=str, nrows=50)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read spreadsheet: {str(e)}")

    headers = list(df.columns)
    headers_lower = [str(c).strip().lower() for c in headers]

    # Smart Category Detection with regex word boundaries
    has_user_name = any(re.search(r'\b(name|inf name|participant|user|guest|influencer)\b', h) for h in headers_lower)
    has_otp_or_cat = any(re.search(r'\b(otp|code|token|passcode|category|cat|tier)\b', h) for h in headers_lower)
    has_courier = any(re.search(r'\b(awb|docket|tracking|courier|consignment)\b', h) for h in headers_lower)
    has_stock = any(re.search(r'\b(vendor|job|inward|printed|print_order)\b', h) for h in headers_lower)
    has_station_master = any(re.search(r'\b(quota|lanyard|gold|silver|vip|coordinator|spoc|delivery address)\b', h) for h in headers_lower)

    if has_user_name and has_otp_or_cat:
        category = "USERS"
        confidence = "High"
    elif has_courier:
        category = "DISPATCHES"
        confidence = "High"
    elif has_stock:
        category = "STOCK"
        confidence = "High"
    elif has_station_master or any(k in h for h in headers_lower for k in ["destination", "centre", "venue"]):
        category = "STATIONS"
        confidence = "High"
    elif has_user_name:
        category = "USERS"
        confidence = "High"
    else:
        category = "USERS"
        confidence = "Medium"

    # Map detected columns
    mappings = []
    for h in headers:
        hl = str(h).strip().lower().replace("_", " ").replace("-", " ")
        matched_target = "—"

        if category == "STATIONS":
            if any(k in hl for k in ["state"]): matched_target = "State"
            elif any(k in hl for k in ["station", "centre", "center", "destination"]): matched_target = "State / Location"
            elif any(k in hl for k in ["date", "event date"]): matched_target = "Event Date"
            elif any(k in hl for k in ["contact", "coordinator", "incharge"]): matched_target = "Coordinator Name"
            elif any(k in hl for k in ["mobile", "phone"]): matched_target = "Mobile Number"
            elif any(k in hl for k in ["address"]): matched_target = "Delivery Address"
            elif any(k in hl for k in ["district"]): matched_target = "District"
            elif any(k in hl for k in ["pin", "zip"]): matched_target = "PIN Code"
            elif any(k in hl for k in ["gold", "influencer"]): matched_target = "Influencer Card Quota"
            elif any(k in hl for k in ["silver", "delegate"]): matched_target = "Special Delegate Card Quota"
            elif any(k in hl for k in ["vip", "executive"]): matched_target = "VIP / Executive Card Quota"
            elif any(k in hl for k in ["lanyard", "pouch"]): matched_target = "Lanyards Quota"
        elif category == "USERS":
            if re.search(r'\b(state)\b', hl): matched_target = "State"
            elif re.search(r'\b(name|inf name|full name|person|guest|influencer)\b', hl): matched_target = "Full Name"
            elif re.search(r'\b(otp|code|token|passcode|qr|serial)\b', hl): matched_target = "Pass Code / OTP"
            elif re.search(r'\b(category|cat|tier|grade)\b', hl): matched_target = "Category"
            elif re.search(r'\b(event location|location|station|venue|city|district)\b', hl): matched_target = "Station / Location"
            elif re.search(r'\b(mobile|phone|contact)\b', hl): matched_target = "Mobile Number"
            elif re.search(r'\b(email)\b', hl): matched_target = "Email Address"
            elif re.search(r'\b(org|company|firm)\b', hl): matched_target = "Organization"
        elif category == "DISPATCHES":
            if any(k in hl for k in ["station", "destination"]): matched_target = "Station Name"
            elif any(k in hl for k in ["courier"]): matched_target = "Courier Partner"
            elif any(k in hl for k in ["awb", "docket"]): matched_target = "AWB Number"
            elif any(k in hl for k in ["date"]): matched_target = "Dispatch Date"

        mappings.append({"column": h, "matched_field": matched_target})

    sample_data = df.head(3).fillna("").to_dict(orient="records")

    return {
        "filename": file.filename,
        "detected_category": category,
        "confidence": confidence,
        "columns": headers,
        "mappings": mappings,
        "sample_preview": sample_data
    }
