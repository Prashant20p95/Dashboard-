"""
EventPass Pro — Pydantic v2 Validation Schemas
All request / response models for the API layer.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ═══════════════════════════════════════════════════════════════════════════════
# GENERIC PAGINATION
# ═══════════════════════════════════════════════════════════════════════════════
class PaginatedResponse(BaseModel):
    items: list[Any] = []
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# EVENTS
# ═══════════════════════════════════════════════════════════════════════════════
class EventCreate(BaseModel):
    event_code: str
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    venue: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    delivery_deadline: Optional[date] = None
    status: str = "DRAFT"
    notes: Optional[str] = None


class EventUpdate(BaseModel):
    event_code: Optional[str] = None
    name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    venue: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    delivery_deadline: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_code: str
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    venue: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    delivery_deadline: Optional[date] = None
    status: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EventSummary(BaseModel):
    """Event summary for dashboard / calendar views."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_code: str
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    delivery_deadline: Optional[date] = None
    status: str
    participant_count: int = 0
    destination_count: int = 0
    dispatch_count: int = 0
    pending_confirmations: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# PARTICIPANTS  (card / printing data — NOT dispatch destinations)
# ═══════════════════════════════════════════════════════════════════════════════
class ParticipantCreate(BaseModel):
    event_id: int
    participant_code: Optional[str] = None
    full_name: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    organization: Optional[str] = None
    card_type: Optional[str] = None
    influencer_tier: Optional[str] = None
    custom_fields: Optional[dict] = None


class ParticipantUpdate(BaseModel):
    full_name: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    organization: Optional[str] = None
    card_type: Optional[str] = None
    influencer_tier: Optional[str] = None
    custom_fields: Optional[dict] = None


class ParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_id: int
    participant_code: Optional[str] = None
    full_name: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    organization: Optional[str] = None
    card_type: Optional[str] = None
    influencer_tier: Optional[str] = None
    custom_fields: Optional[dict] = None
    source_import_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════════════════
# ORGANISERS  (reusable master directory)
# ═══════════════════════════════════════════════════════════════════════════════
class OrganiserCreate(BaseModel):
    destination_code: Optional[str] = None
    organiser_name: str
    organization: Optional[str] = None
    contact_person: Optional[str] = None
    mobile: Optional[str] = None
    alt_phone: Optional[str] = None
    email: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    landmark: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin: Optional[str] = None
    destination_type: str = "REGIONAL_ORGANISER"
    notes: Optional[str] = None


class OrganiserUpdate(BaseModel):
    organiser_name: Optional[str] = None
    organization: Optional[str] = None
    contact_person: Optional[str] = None
    mobile: Optional[str] = None
    alt_phone: Optional[str] = None
    email: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    landmark: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin: Optional[str] = None
    destination_type: Optional[str] = None
    notes: Optional[str] = None


class OrganiserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    destination_code: str
    organiser_name: str
    organization: Optional[str] = None
    contact_person: Optional[str] = None
    mobile: Optional[str] = None
    alt_phone: Optional[str] = None
    email: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    landmark: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin: Optional[str] = None
    destination_type: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════════════════
# EVENT DESTINATIONS  (event-specific dispatch targets)
# ═══════════════════════════════════════════════════════════════════════════════
class EventDestinationCreate(BaseModel):
    event_id: int
    organiser_id: Optional[int] = None
    destination_name: str
    event_date: Optional[date] = None
    contact_person: Optional[str] = None
    mobile: Optional[str] = None
    alt_phone: Optional[str] = None
    email: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    landmark: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin: Optional[str] = None
    required_quantities: Optional[dict] = None
    destination_notes: Optional[str] = None


class EventDestinationUpdate(BaseModel):
    organiser_id: Optional[int] = None
    destination_name: Optional[str] = None
    event_date: Optional[date] = None
    contact_person: Optional[str] = None
    mobile: Optional[str] = None
    alt_phone: Optional[str] = None
    email: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    landmark: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin: Optional[str] = None
    required_quantities: Optional[dict] = None
    destination_notes: Optional[str] = None


class EventDestinationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_id: int
    organiser_id: Optional[int] = None
    destination_name: str
    event_date: Optional[date] = None
    contact_person: Optional[str] = None
    mobile: Optional[str] = None
    alt_phone: Optional[str] = None
    email: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    landmark: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin: Optional[str] = None
    required_quantities: Optional[dict] = None
    destination_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════════════════
# PRINTING JOBS
# ═══════════════════════════════════════════════════════════════════════════════
class PrintingJobCreate(BaseModel):
    event_id: int
    collateral_code: str
    vendor_name: Optional[str] = None
    vendor_contact: Optional[str] = None
    quantity_required: int = 0
    quantity_sent: int = 0
    date_sent: Optional[date] = None
    expected_receipt_date: Optional[date] = None
    status: str = "PENDING"
    notes: Optional[str] = None


class PrintingJobUpdate(BaseModel):
    vendor_name: Optional[str] = None
    vendor_contact: Optional[str] = None
    quantity_required: Optional[int] = None
    quantity_sent: Optional[int] = None
    date_sent: Optional[date] = None
    expected_receipt_date: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class PrintingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_number: str
    event_id: int
    collateral_code: str
    vendor_name: Optional[str] = None
    vendor_contact: Optional[str] = None
    quantity_required: int = 0
    quantity_sent: int = 0
    date_sent: Optional[date] = None
    expected_receipt_date: Optional[date] = None
    status: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    total_received: int = 0  # computed field


# ═══════════════════════════════════════════════════════════════════════════════
# PHYSICAL RECEIPTS
# ═══════════════════════════════════════════════════════════════════════════════
class PhysicalReceiptCreate(BaseModel):
    job_id: int
    event_id: int
    collateral_code: str
    quantity_received: int
    receipt_date: Optional[date] = None
    received_by: Optional[str] = None
    challan_number: Optional[str] = None
    notes: Optional[str] = None


class PhysicalReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_id: int
    event_id: int
    collateral_code: str
    quantity_received: int
    receipt_date: Optional[date] = None
    received_by: Optional[str] = None
    challan_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════════════════
# STOCK
# ═══════════════════════════════════════════════════════════════════════════════
class StockSummaryItem(BaseModel):
    collateral_code: str
    collateral_name: str = ""
    category: str = ""
    total_received: int = 0
    total_dispatched: int = 0
    adjustments: int = 0
    current_stock: int = 0


class StockTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_id: int
    collateral_code: str
    transaction_type: str
    quantity: int
    balance_after: Optional[int] = None
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class StockAdjustRequest(BaseModel):
    event_id: int
    collateral_code: str
    quantity: int
    notes: str   # mandatory — explain every adjustment


# ═══════════════════════════════════════════════════════════════════════════════
# DISPATCH BATCHES
# ═══════════════════════════════════════════════════════════════════════════════
class DispatchBatchCreate(BaseModel):
    event_id: int
    name: Optional[str] = None
    notes: Optional[str] = None


class DispatchBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    batch_code: str
    event_id: int
    name: Optional[str] = None
    total_destinations: int = 0
    status: str
    notes: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════════════════
# DISPATCHES  (shipments to organisers, ~120 per event, NOT 110,000)
# ═══════════════════════════════════════════════════════════════════════════════
class DispatchItemCreate(BaseModel):
    collateral_code: str
    quantity: int = Field(..., gt=0)


class DispatchCreate(BaseModel):
    batch_id: Optional[int] = None
    event_id: int
    destination_id: int
    dispatch_date: Optional[date] = None
    courier_partner: Optional[str] = None
    courier_name_other: Optional[str] = None
    awb_number: Optional[str] = None
    via: Optional[str] = "Surface"
    box_count: Optional[str] = "1 Box"
    courier_status: Optional[str] = "IN_TRANSIT"
    expected_delivery_date: Optional[date] = None
    notes: Optional[str] = None
    items: list[DispatchItemCreate] = []


class BulkDispatchEntry(BaseModel):
    destination_id: int
    items: list[DispatchItemCreate] = Field(..., min_length=1)


class BulkDispatchCreate(BaseModel):
    event_id: int
    batch_id: Optional[int] = None
    dispatch_date: Optional[date] = None
    courier_partner: Optional[str] = None
    entries: list[BulkDispatchEntry] = Field(..., min_length=1)


class DispatchItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    dispatch_id: int
    collateral_code: str
    quantity: int
    created_at: Optional[datetime] = None


class DispatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    dispatch_code: str
    batch_id: Optional[int] = None
    event_id: int
    destination_id: int
    hist_organiser_name: Optional[str] = None
    hist_contact_person: Optional[str] = None
    hist_mobile: Optional[str] = None
    hist_address_line1: Optional[str] = None
    hist_address_line2: Optional[str] = None
    hist_landmark: Optional[str] = None
    hist_district: Optional[str] = None
    hist_city: Optional[str] = None
    hist_state: Optional[str] = None
    hist_pin: Optional[str] = None
    dispatch_date: Optional[date] = None
    courier_partner: Optional[str] = None
    courier_name_other: Optional[str] = None
    awb_number: Optional[str] = None
    via: Optional[str] = "Surface"
    box_count: Optional[str] = "1 Box"
    expected_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None
    courier_status: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: list[DispatchItemResponse] = []


class DispatchStatusUpdate(BaseModel):
    courier_status: Optional[str] = None
    courier_partner: Optional[str] = None
    courier_name_other: Optional[str] = None
    awb_number: Optional[str] = None
    via: Optional[str] = None
    box_count: Optional[str] = None
    dispatch_date: Optional[date] = None
    expected_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None
    notes: Optional[str] = None
    items: Optional[list[DispatchItemCreate]] = None


# ═══════════════════════════════════════════════════════════════════════════════
# DELIVERY CONFIRMATIONS
# ═══════════════════════════════════════════════════════════════════════════════
class DeliveryConfirmationCreate(BaseModel):
    dispatch_id: Optional[int] = None
    confirmation_status: str = "PENDING"
    confirmed_by_name: Optional[str] = None
    confirmed_by_user: Optional[str] = None
    confirmation_method: Optional[str] = None
    confirmation_date: Optional[datetime] = None
    issue_description: Optional[str] = None
    notes: Optional[str] = None


class DeliveryConfirmationUpdate(BaseModel):
    confirmation_status: Optional[str] = None
    confirmed_by_name: Optional[str] = None
    confirmed_by_user: Optional[str] = None
    confirmation_method: Optional[str] = None
    confirmation_date: Optional[datetime] = None
    issue_description: Optional[str] = None
    notes: Optional[str] = None


class DeliveryConfirmationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    dispatch_id: int
    confirmation_status: str
    confirmed_by_name: Optional[str] = None
    confirmed_by_user: Optional[str] = None
    confirmation_method: Optional[str] = None
    confirmation_date: Optional[datetime] = None
    issue_description: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════════════════
# BILLING — PRINTING INVOICES
# ═══════════════════════════════════════════════════════════════════════════════
class PrintingInvoiceCreate(BaseModel):
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    event_id: Optional[int] = None
    job_id: Optional[int] = None
    total_amount: float = 0
    gst_amount: float = 0
    invoice_date: Optional[date] = None
    submission_date: Optional[date] = None
    payment_status: str = "PENDING"
    notes: Optional[str] = None


class PrintingInvoiceUpdate(BaseModel):
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    event_id: Optional[int] = None
    job_id: Optional[int] = None
    total_amount: Optional[float] = None
    gst_amount: Optional[float] = None
    invoice_date: Optional[date] = None
    submission_date: Optional[date] = None
    payment_status: Optional[str] = None
    payment_date: Optional[date] = None
    notes: Optional[str] = None


class PrintingInvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    event_id: Optional[int] = None
    job_id: Optional[int] = None
    total_amount: float = 0
    gst_amount: float = 0
    invoice_date: Optional[date] = None
    submission_date: Optional[date] = None
    payment_status: str
    payment_date: Optional[date] = None
    file_path: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════════════════
# BILLING — COURIER INVOICES
# ═══════════════════════════════════════════════════════════════════════════════
class CourierInvoiceCreate(BaseModel):
    courier_partner: Optional[str] = None
    invoice_number: Optional[str] = None
    event_id: Optional[int] = None
    billing_period_start: Optional[date] = None
    billing_period_end: Optional[date] = None
    consignments_count: int = 0
    billed_weight_kg: float = 0
    total_amount: float = 0
    submission_date: Optional[date] = None
    payment_status: str = "PENDING"
    notes: Optional[str] = None


class CourierInvoiceUpdate(BaseModel):
    courier_partner: Optional[str] = None
    invoice_number: Optional[str] = None
    event_id: Optional[int] = None
    billing_period_start: Optional[date] = None
    billing_period_end: Optional[date] = None
    consignments_count: Optional[int] = None
    billed_weight_kg: Optional[float] = None
    total_amount: Optional[float] = None
    submission_date: Optional[date] = None
    payment_status: Optional[str] = None
    payment_date: Optional[date] = None
    notes: Optional[str] = None


class CourierInvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    courier_partner: Optional[str] = None
    invoice_number: Optional[str] = None
    event_id: Optional[int] = None
    billing_period_start: Optional[date] = None
    billing_period_end: Optional[date] = None
    consignments_count: int = 0
    billed_weight_kg: float = 0
    total_amount: float = 0
    submission_date: Optional[date] = None
    payment_status: str
    payment_date: Optional[date] = None
    file_path: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════════════════
# IMPORT
# ═══════════════════════════════════════════════════════════════════════════════
class ImportSheetInfo(BaseModel):
    sheet_name: str
    sheet_index: int = 0
    header_row: Optional[int] = None
    total_rows: int = 0
    total_columns: int = 0
    detected_headers: list[str] = []
    sample_data: list[dict] = []
    detected_category: Optional[str] = None
    suggested_mapping: Optional[dict] = None


class ImportFileAnalysis(BaseModel):
    file_id: int
    original_filename: str
    detected_category: Optional[str] = None
    total_rows: int = 0
    sheets: list[ImportSheetInfo] = []


class ImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_name: Optional[str] = None
    status: str
    total_files: int = 0
    uploaded_by: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    files: list[ImportFileAnalysis] = []


class ImportApproveRequest(BaseModel):
    column_mapping: dict   # {"source_col": "target_field", ...}
    target_category: str   # PARTICIPANT_CARD_DATA | ORGANISER_DESTINATIONS
    event_id: Optional[int] = None


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════
class ExportColumnDef(BaseModel):
    header: str          # Column header in Excel
    field: str           # Source field key
    format: Optional[str] = None


class ExportTemplateCreate(BaseModel):
    template_name: str
    target_scope: Optional[str] = None
    column_definitions: list[ExportColumnDef] = []
    sheet_name: Optional[str] = None
    header_start_row: int = 1
    date_format: Optional[str] = None


class ExportTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    template_name: str
    target_scope: Optional[str] = None
    column_definitions: list[ExportColumnDef] = []
    sheet_name: Optional[str] = None
    header_start_row: int = 1
    date_format: Optional[str] = None
    is_system_default: bool = False
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None


class ExportGenerateRequest(BaseModel):
    template_id: Optional[int] = None
    event_id: Optional[int] = None
    export_scope: str = "ALL"          # ALL | STATE_WISE | DISTRICT_WISE | DESTINATION_WISE | SELECTED
    filters: Optional[dict] = None     # {"state": "Maharashtra", "courier_status": "PENDING"}
    destination_ids: Optional[list[int]] = None


class ExportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    template_id: Optional[int] = None
    event_id: Optional[int] = None
    export_scope: Optional[str] = None
    generated_files: list[dict] = []
    version_tag: Optional[str] = None
    row_count: int = 0
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════════════════
# COLLATERAL ITEMS
# ═══════════════════════════════════════════════════════════════════════════════
class CollateralItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    category: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# EVENT OPERATIONAL SUMMARY (destination-level status)
# ═══════════════════════════════════════════════════════════════════════════════
class DestinationDispatchItem(BaseModel):
    dispatch_id: int
    dispatch_code: str
    dispatch_date: Optional[date] = None
    items: dict = {}  # {collateral_code: quantity}
    awb_number: Optional[str] = None
    courier_partner: Optional[str] = None
    courier_status: Optional[str] = None
    confirmation_status: Optional[str] = None
    confirmation_date: Optional[str] = None
    confirmed_by_name: Optional[str] = None
    box_count: Optional[str] = None
    actual_delivery_date: Optional[date] = None
    notes: Optional[str] = None


class DestinationStatusSummary(BaseModel):
    destination_id: int
    destination_name: Optional[str] = None
    event_date: Optional[date] = None
    organiser_name: Optional[str] = None
    contact_person: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    address_line1: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin: Optional[str] = None
    required: dict = {}  # {collateral_code: qty}
    sent: dict = {}      # {collateral_code: qty}
    remaining: dict = {} # {collateral_code: qty}
    shipment_count: int = 0
    latest_dispatch_date: Optional[date] = None
    latest_awb: Optional[str] = None
    latest_courier: Optional[str] = None
    latest_delivery_date: Optional[date] = None
    box_count: Optional[str] = None
    courier_status: Optional[str] = None
    confirmation_status: Optional[str] = None
    confirmation_date: Optional[str] = None
    confirmed_by_name: Optional[str] = None
    fulfillment: str = "NOT_STARTED"  # NOT_STARTED | PARTIAL | COMPLETE | OVER_DISPATCHED
    dispatches: list[DestinationDispatchItem] = []


class EventOperationalSummary(BaseModel):
    event_id: int
    event_name: str
    event_code: str
    city: Optional[str] = None
    state: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    delivery_deadline: Optional[date] = None
    status: str = ""
    participant_count: int = 0
    destination_summary: list[DestinationStatusSummary] = []
    stock_summary: dict = {}  # {collateral_code: qty}
    total_destinations: int = 0
    destinations_not_dispatched: int = 0
    destinations_partial: int = 0
    destinations_complete: int = 0
    total_shipments: int = 0
    shipments_in_transit: int = 0
    confirmations_pending: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
class ActionRequiredItem(BaseModel):
    severity: str = "warning"   # critical | warning | info
    message: str
    count: int = 0
    link_module: Optional[str] = None
    link_filter: Optional[dict] = None


class EventDashboardSummary(BaseModel):
    event_id: int
    event_name: str
    event_code: str
    city: Optional[str] = None
    state: Optional[str] = None
    start_date: Optional[date] = None
    delivery_deadline: Optional[date] = None
    status: str
    participant_count: int = 0
    cards_printed: int = 0
    cards_received: int = 0
    destination_count: int = 0
    destinations_fulfilled: int = 0
    destinations_partial: int = 0
    destinations_pending: int = 0
    total_shipments: int = 0
    dispatched_quantity: int = 0
    remaining_stock: dict = {}
    deliveries_complete: int = 0
    confirmations_pending: int = 0
    printing_bills_pending: int = 0
    courier_bills_pending: int = 0


class DashboardResponse(BaseModel):
    active_events: list[EventDashboardSummary] = []
    action_required: list[ActionRequiredItem] = []
    total_events: int = 0
    total_participants: int = 0
    total_organisers: int = 0
    # NEW operational KPIs
    total_dispatches: int = 0
    dispatches_in_transit: int = 0
    delivered_awaiting_confirmation: int = 0
    destinations_requiring_dispatch: int = 0
    upcoming_deadlines: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG
# ═══════════════════════════════════════════════════════════════════════════════
class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: Optional[int] = None
    entity_name: Optional[str] = None
    entity_id: Optional[int] = None
    action: Optional[str] = None
    old_values_json: Optional[str] = None
    new_values_json: Optional[str] = None
    description: Optional[str] = None
    timestamp: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════════════════
# EVENT RECONCILIATION
# ═══════════════════════════════════════════════════════════════════════════════
class ReconciliationException(BaseModel):
    severity: str           # critical | warning | info
    category: str           # delivery | stock | billing | data
    message: str
    count: int = 0


class EventReconciliation(BaseModel):
    event_id: int
    event_name: str
    participant_count: int = 0
    printing_summary: dict = {}     # {collateral_code: {required, sent, received}}
    stock_summary: dict = {}        # {collateral_code: {received, dispatched, remaining}}
    dispatch_summary: dict = {}     # {total_destinations, total_dispatched, by_status}
    delivery_summary: dict = {}     # {delivered, pending, rto, confirmed, unconfirmed}
    billing_summary: dict = {}      # {printing_total, courier_total, paid, pending}
    exceptions: list[ReconciliationException] = []
