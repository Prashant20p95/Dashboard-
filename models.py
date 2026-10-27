"""
EventPass Pro — SQLAlchemy ORM Models  (22 tables)

CRITICAL BUSINESS RULE:
    Participants (110,000 card/printing records)
      ≠
    Organisers / EventDestinations (~120 dispatch targets)

    These are completely separate entities.
    Participant records NEVER automatically create dispatch records.
"""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, Date, DateTime,
    ForeignKey, Index,
)
from sqlalchemy.orm import relationship

from database import Base


# ═══════════════════════════════════════════════════════════════════════════════
# 1. USERS
# ═══════════════════════════════════════════════════════════════════════════════
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(200))
    email = Column(String(200))
    hashed_password = Column(String(200))
    role = Column(String(50), default="VIEWER")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. EVENTS
# ═══════════════════════════════════════════════════════════════════════════════
class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    event_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(300), nullable=False)
    city = Column(String(100))
    state = Column(String(100))
    venue = Column(String(300))
    start_date = Column(Date)
    end_date = Column(Date)
    delivery_deadline = Column(Date)
    status = Column(String(50), default="DRAFT", index=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    participants = relationship("Participant", back_populates="event", lazy="dynamic")
    printing_jobs = relationship("PrintingJob", back_populates="event")
    event_destinations = relationship("EventDestination", back_populates="event")
    dispatch_batches = relationship("DispatchBatch", back_populates="event")
    dispatches = relationship("Dispatch", back_populates="event")
    physical_receipts = relationship("PhysicalReceipt", back_populates="event")
    printing_invoices = relationship("PrintingInvoice", back_populates="event")
    courier_invoices = relationship("CourierInvoice", back_populates="event")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. COLLATERAL ITEMS  (Reference / Seed Data)
# ═══════════════════════════════════════════════════════════════════════════════
class CollateralItem(Base):
    __tablename__ = "collateral_items"

    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    category = Column(String(50))     # DATA_DRIVEN_CARD | FIXED_FORMAT_CARD | COLLATERAL
    unit = Column(String(20), default="pcs")
    description = Column(Text)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. PARTICIPANTS — Card / printing data.  NOT dispatch destinations!
#    110,000+ records per event.  No FK to dispatches or logistics.
# ═══════════════════════════════════════════════════════════════════════════════
class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    participant_code = Column(String(50))
    full_name = Column(String(300))
    mobile = Column(String(20))
    email = Column(String(200))
    organization = Column(String(300))
    card_type = Column(String(50))        # PRIMARY_PASS | SECONDARY_DELEGATE | VIP_TEAM_CARD
    influencer_tier = Column(String(50))  # MEGA | MACRO | MICRO | VIP | SPEAKER | null
    custom_fields_json = Column(Text)     # Arbitrary extra Excel columns as JSON
    source_import_id = Column(Integer, ForeignKey("import_jobs.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event = relationship("Event", back_populates="participants")

    __table_args__ = (
        Index("ix_part_event_card", "event_id", "card_type"),
        Index("ix_part_mobile", "mobile"),
        Index("ix_part_name", "full_name"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ORGANISERS — Reusable master directory.
#    An organiser identity can participate in multiple events.
# ═══════════════════════════════════════════════════════════════════════════════
class Organiser(Base):
    __tablename__ = "organisers"

    id = Column(Integer, primary_key=True)
    destination_code = Column(String(50), unique=True, nullable=False, index=True)
    organiser_name = Column(String(300), nullable=False)
    organization = Column(String(300))
    contact_person = Column(String(200))
    mobile = Column(String(20))
    alt_phone = Column(String(20))
    email = Column(String(200))
    address_line1 = Column(String(500))
    address_line2 = Column(String(500))
    landmark = Column(String(300))
    district = Column(String(100))
    city = Column(String(100))
    state = Column(String(100))
    pin = Column(String(10))
    destination_type = Column(String(50), default="REGIONAL_ORGANISER")
    notes = Column(Text)
    source_import_id = Column(Integer, ForeignKey("import_jobs.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event_destinations = relationship("EventDestination", back_populates="organiser")

    __table_args__ = (
        Index("ix_org_state_district", "state", "district"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 6. EVENT DESTINATIONS — Event-specific dispatch targets.
#    Links an organiser (optional) to a specific event with event-specific
#    contact, address, and required quantities.
#    Dispatches point HERE, not directly at the organiser master.
# ═══════════════════════════════════════════════════════════════════════════════
class EventDestination(Base):
    __tablename__ = "event_destinations"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    organiser_id = Column(Integer, ForeignKey("organisers.id"), nullable=True)
    destination_name = Column(String(300), nullable=False)
    event_date = Column(Date, nullable=True)
    contact_person = Column(String(200))
    mobile = Column(String(20))
    alt_phone = Column(String(20))
    email = Column(String(200))
    address_line1 = Column(String(500))
    address_line2 = Column(String(500))
    landmark = Column(String(300))
    district = Column(String(100))
    city = Column(String(100))
    state = Column(String(100))
    pin = Column(String(10))
    required_quantities_json = Column(Text)   # {"INFLUENCER_COUPON": 2000, "LANYARD": 2000}
    destination_notes = Column(Text)
    source_import_id = Column(Integer, ForeignKey("import_jobs.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event = relationship("Event", back_populates="event_destinations")
    organiser = relationship("Organiser", back_populates="event_destinations")
    dispatches = relationship("Dispatch", back_populates="destination")

    @property
    def required_quantities(self):
        """Parse required_quantities_json into a dict."""
        if self.required_quantities_json:
            try:
                import json
                return json.loads(self.required_quantities_json)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    __table_args__ = (
        Index("ix_evdest_event", "event_id"),
        Index("ix_evdest_state", "state", "district"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 7. PRINTING JOBS
# ═══════════════════════════════════════════════════════════════════════════════
class PrintingJob(Base):
    __tablename__ = "printing_jobs"

    id = Column(Integer, primary_key=True)
    job_number = Column(String(50), unique=True, nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    collateral_code = Column(String(50), ForeignKey("collateral_items.code"), nullable=False)
    vendor_name = Column(String(300))
    vendor_contact = Column(String(200))
    quantity_required = Column(Integer, default=0)
    quantity_sent = Column(Integer, default=0)
    date_sent = Column(Date)
    expected_receipt_date = Column(Date)
    status = Column(String(50), default="PENDING")
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="printing_jobs")
    physical_receipts = relationship("PhysicalReceipt", back_populates="printing_job")
    invoices = relationship("PrintingInvoice", back_populates="printing_job")


# ═══════════════════════════════════════════════════════════════════════════════
# 8. PHYSICAL RECEIPTS
# ═══════════════════════════════════════════════════════════════════════════════
class PhysicalReceipt(Base):
    __tablename__ = "physical_receipts"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("printing_jobs.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    collateral_code = Column(String(50), ForeignKey("collateral_items.code"), nullable=False)
    quantity_received = Column(Integer, nullable=False)
    receipt_date = Column(Date)
    received_by = Column(String(200))
    challan_number = Column(String(100))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    printing_job = relationship("PrintingJob", back_populates="physical_receipts")
    event = relationship("Event", back_populates="physical_receipts")


# ═══════════════════════════════════════════════════════════════════════════════
# 9. STOCK TRANSACTIONS — Ledger for physical inventory.
#    Stock(event, item) = SUM(quantity) WHERE event_id AND collateral_code
# ═══════════════════════════════════════════════════════════════════════════════
class StockTransaction(Base):
    __tablename__ = "stock_transactions"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    collateral_code = Column(String(50), ForeignKey("collateral_items.code"), nullable=False)
    transaction_type = Column(String(50), nullable=False)   # RECEIPT | DISPATCH | ADJUSTMENT | TRANSFER
    quantity = Column(Integer, nullable=False)               # +ve for in, −ve for out
    balance_after = Column(Integer)
    reference_type = Column(String(50))    # PHYSICAL_RECEIPT | DISPATCH_ITEM | MANUAL_ADJUSTMENT | STOCK_TRANSFER
    reference_id = Column(Integer)
    created_by = Column(String(200))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_stock_event_item", "event_id", "collateral_code"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 10. DISPATCH BATCHES
# ═══════════════════════════════════════════════════════════════════════════════
class DispatchBatch(Base):
    __tablename__ = "dispatch_batches"

    id = Column(Integer, primary_key=True)
    batch_code = Column(String(50), unique=True, nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    name = Column(String(300))
    total_destinations = Column(Integer, default=0)
    status = Column(String(50), default="DRAFT")
    notes = Column(Text)
    created_by = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event = relationship("Event", back_populates="dispatch_batches")
    dispatches = relationship("Dispatch", back_populates="batch")


# ═══════════════════════════════════════════════════════════════════════════════
# 11. DISPATCHES — Physical shipments to event destinations (~120, NOT 110,000).
#     Contains a historical address snapshot frozen at creation time.
# ═══════════════════════════════════════════════════════════════════════════════
class Dispatch(Base):
    __tablename__ = "dispatches"

    id = Column(Integer, primary_key=True)
    dispatch_code = Column(String(50), unique=True, nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("dispatch_batches.id"), nullable=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    destination_id = Column(Integer, ForeignKey("event_destinations.id"), nullable=False)

    # ── Historical Address Snapshot (frozen at dispatch creation) ──
    hist_organiser_name = Column(String(300))
    hist_contact_person = Column(String(200))
    hist_mobile = Column(String(20))
    hist_address_line1 = Column(String(500))
    hist_address_line2 = Column(String(500))
    hist_landmark = Column(String(300))
    hist_district = Column(String(100))
    hist_city = Column(String(100))
    hist_state = Column(String(100))
    hist_pin = Column(String(10))

    # ── Logistics ──
    dispatch_date = Column(Date)
    courier_partner = Column(String(100))
    courier_name_other = Column(String(200))
    awb_number = Column(String(100))
    via = Column(String(50), default="Surface")
    box_count = Column(String(50), default="1 Box")
    expected_delivery_date = Column(Date)
    actual_delivery_date = Column(Date)
    courier_status = Column(String(50), default="PENDING")
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event = relationship("Event", back_populates="dispatches")
    batch = relationship("DispatchBatch", back_populates="dispatches")
    destination = relationship("EventDestination", back_populates="dispatches")
    items = relationship("DispatchItem", back_populates="dispatch", cascade="all, delete-orphan")
    delivery_confirmation = relationship(
        "DeliveryConfirmation", back_populates="dispatch", uselist=False
    )

    __table_args__ = (
        Index("ix_dsp_event_status", "event_id", "courier_status"),
        Index("ix_dsp_batch", "batch_id"),
        Index("ix_dsp_awb", "awb_number"),
        Index("ix_dsp_state", "hist_state"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 12. DISPATCH ITEMS — Collateral bundles within a single dispatch.
#     One shipment → 2,000 Cards + 2,000 Lanyards + 2,000 Pouches
# ═══════════════════════════════════════════════════════════════════════════════
class DispatchItem(Base):
    __tablename__ = "dispatch_items"

    id = Column(Integer, primary_key=True)
    dispatch_id = Column(Integer, ForeignKey("dispatches.id"), nullable=False)
    collateral_code = Column(String(50), ForeignKey("collateral_items.code"), nullable=False)
    quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    dispatch = relationship("Dispatch", back_populates="items")

    __table_args__ = (
        Index("ix_di_dispatch", "dispatch_id"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 13. DELIVERY CONFIRMATIONS — Separate from courier tracking.
#     Courier "Delivered" ≠ Organiser confirmed receipt.
# ═══════════════════════════════════════════════════════════════════════════════
class DeliveryConfirmation(Base):
    __tablename__ = "delivery_confirmations"

    id = Column(Integer, primary_key=True)
    dispatch_id = Column(Integer, ForeignKey("dispatches.id"), unique=True, nullable=False)
    confirmation_status = Column(String(50), default="PENDING")
    confirmed_by_name = Column(String(200))
    confirmed_by_user = Column(String(200))
    confirmation_method = Column(String(50))     # PHONE_CALL | EMAIL | WHATSAPP | IN_PERSON
    confirmation_date = Column(DateTime)
    issue_description = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    dispatch = relationship("Dispatch", back_populates="delivery_confirmation")


# ═══════════════════════════════════════════════════════════════════════════════
# 14. PRINTING INVOICES
# ═══════════════════════════════════════════════════════════════════════════════
class PrintingInvoice(Base):
    __tablename__ = "printing_invoices"

    id = Column(Integer, primary_key=True)
    vendor_name = Column(String(300))
    invoice_number = Column(String(100))
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    job_id = Column(Integer, ForeignKey("printing_jobs.id"), nullable=True)
    total_amount = Column(Float, default=0)
    gst_amount = Column(Float, default=0)
    invoice_date = Column(Date)
    submission_date = Column(Date)
    payment_status = Column(String(50), default="PENDING")
    payment_date = Column(Date)
    file_path = Column(String(500))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="printing_invoices")
    printing_job = relationship("PrintingJob", back_populates="invoices")


# ═══════════════════════════════════════════════════════════════════════════════
# 15. COURIER INVOICES
# ═══════════════════════════════════════════════════════════════════════════════
class CourierInvoice(Base):
    __tablename__ = "courier_invoices"

    id = Column(Integer, primary_key=True)
    courier_partner = Column(String(100))
    invoice_number = Column(String(100))
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    billing_period_start = Column(Date)
    billing_period_end = Column(Date)
    consignments_count = Column(Integer, default=0)
    billed_weight_kg = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    submission_date = Column(Date)
    payment_status = Column(String(50), default="PENDING")
    payment_date = Column(Date)
    file_path = Column(String(500))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="courier_invoices")


# ═══════════════════════════════════════════════════════════════════════════════
# 16. IMPORT JOBS
# ═══════════════════════════════════════════════════════════════════════════════
class ImportJob(Base):
    __tablename__ = "import_jobs"

    id = Column(Integer, primary_key=True)
    job_name = Column(String(300))
    status = Column(String(50), default="UPLOADED")
    total_files = Column(Integer, default=0)
    uploaded_by = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    files = relationship("ImportFile", back_populates="job")


# ═══════════════════════════════════════════════════════════════════════════════
# 17. IMPORT FILES
# ═══════════════════════════════════════════════════════════════════════════════
class ImportFile(Base):
    __tablename__ = "import_files"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("import_jobs.id"), nullable=False)
    original_filename = Column(String(500))
    stored_filepath = Column(String(500))
    file_hash = Column(String(64))
    detected_category = Column(String(50))
    total_rows = Column(Integer, default=0)
    imported_rows = Column(Integer, default=0)
    duplicate_rows = Column(Integer, default=0)
    rejected_rows = Column(Integer, default=0)
    conflict_rows = Column(Integer, default=0)
    column_mapping_json = Column(Text)
    status = Column(String(50), default="PENDING")
    error_report_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("ImportJob", back_populates="files")
    sheets = relationship("ImportSheet", back_populates="file")


# ═══════════════════════════════════════════════════════════════════════════════
# 18. IMPORT SHEETS
# ═══════════════════════════════════════════════════════════════════════════════
class ImportSheet(Base):
    __tablename__ = "import_sheets"

    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("import_files.id"), nullable=False)
    sheet_name = Column(String(200))
    sheet_index = Column(Integer)
    header_row = Column(Integer)
    total_rows = Column(Integer, default=0)
    total_columns = Column(Integer, default=0)
    detected_headers_json = Column(Text)
    sample_data_json = Column(Text)
    detected_category = Column(String(50))
    suggested_mapping_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    file = relationship("ImportFile", back_populates="sheets")


# ═══════════════════════════════════════════════════════════════════════════════
# 19. IMPORT MAPPINGS — Learned column-alias memory
# ═══════════════════════════════════════════════════════════════════════════════
class ImportMapping(Base):
    __tablename__ = "import_mappings"

    id = Column(Integer, primary_key=True)
    source_alias = Column(String(200), nullable=False)
    target_field = Column(String(100), nullable=False)
    category = Column(String(50))
    vendor_hint = Column(String(200))
    usage_count = Column(Integer, default=1)
    last_used_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_imap_alias", "source_alias", "category"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 20. EXPORT TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════
class ExportTemplate(Base):
    __tablename__ = "export_templates"

    id = Column(Integer, primary_key=True)
    template_name = Column(String(200), unique=True, nullable=False)
    target_scope = Column(String(50))
    column_definitions_json = Column(Text)
    source_template_filepath = Column(String(500))
    sheet_name = Column(String(100))
    header_start_row = Column(Integer, default=1)
    date_format = Column(String(50))
    is_system_default = Column(Boolean, default=False)
    created_by = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def column_definitions(self):
        if self.column_definitions_json:
            try:
                import json
                return json.loads(self.column_definitions_json)
            except Exception:
                return []
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# 21. EXPORT JOBS
# ═══════════════════════════════════════════════════════════════════════════════
class ExportJob(Base):
    __tablename__ = "export_jobs"

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("export_templates.id"), nullable=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    export_scope = Column(String(50))
    filter_criteria_json = Column(Text)
    generated_files_json = Column(Text)
    version_tag = Column(String(20))
    row_count = Column(Integer, default=0)
    created_by = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def generated_files(self):
        if self.generated_files_json:
            try:
                import json
                return json.loads(self.generated_files_json)
            except Exception:
                return []
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# 22. AUDIT LOGS
# ═══════════════════════════════════════════════════════════════════════════════
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    entity_name = Column(String(100))
    entity_id = Column(Integer)
    action = Column(String(50))
    old_values_json = Column(Text)
    new_values_json = Column(Text)
    description = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_audit_entity", "entity_name", "entity_id"),
        Index("ix_audit_time", "timestamp"),
    )
