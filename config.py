"""
OpsCommand — Enterprise Operations & Logistics Command Configuration
====================================================================
Single source of truth for organization settings, branding, SKU items, 
geographical regions, courier tracking integrations, and database config.

All values can be overridden via environment variables or a .env file.
"""
import os
from typing import List, Dict, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── 1. Organization & Portal Branding ──────────────────────────────────────────
ORGANIZATION_NAME = os.getenv("ORGANIZATION_NAME", "Operations Command")
PORTAL_TITLE = os.getenv("PORTAL_TITLE", "Operations & Consignment Dispatch Portal")
PORTAL_SUBTITLE = os.getenv("PORTAL_SUBTITLE", "Pan-Region Hub Logistics & Delivery Verification System")
APP_VERSION = os.getenv("APP_VERSION", "2.0.0")

# Support & Operational Inquiries
SUPPORT_PHONE = os.getenv("SUPPORT_PHONE", "+91 98765 43210")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "operations@command.internal")
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "INR")

# ── 2. Database & Server Configuration ─────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"sqlite:///{os.path.join(BASE_DIR, 'operations.db')}"
)
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

# Operational Risk Alert Threshold (in days)
AT_RISK_THRESHOLD_DAYS = int(os.getenv("AT_RISK_THRESHOLD_DAYS", "3"))

# ── 3. Configurable Collateral / SKU Items ─────────────────────────────────────
# Organizations can customize tracked items according to their operational needs.
# Default setup provides 4 standard operational categories:
TRACKED_ITEMS: List[Dict[str, Any]] = [
    {
        "code": "ITEM_PRIMARY",
        "name": "Primary Pass / Kit",
        "category": "CORE",
        "unit": "pcs",
        "default_qty": 500,
        "description": "Standard participant pass, attendee kit, or essential item package."
    },
    {
        "code": "ITEM_SECONDARY",
        "name": "Secondary Pack",
        "category": "CORE",
        "unit": "pcs",
        "default_qty": 100,
        "description": "Special delegate passes, auxiliary collateral, or secondary package."
    },
    {
        "code": "ITEM_VIP",
        "name": "VIP / Executive Kit",
        "category": "PREMIUM",
        "unit": "pcs",
        "default_qty": 50,
        "description": "Executive pass, VIP package, or premium identification bundle."
    },
    {
        "code": "ITEM_ACCESSORY",
        "name": "Lanyards & Badges",
        "category": "ACCESSORY",
        "unit": "pcs",
        "default_qty": 650,
        "description": "Identification lanyards, badge holders, or stationery accessories."
    }
]

# Quick lookup by item code
ITEM_MAP = {item["code"]: item for item in TRACKED_ITEMS}

# ── 4. Courier Partners & Tracking Integrations ────────────────────────────────
# Maps courier partner name to public AWB tracking URL template.
# {awb} placeholder is dynamically replaced with the consignment tracking number.
COURIER_PARTNERS: Dict[str, str] = {
    "BlueDart": "https://www.bluedart.com/tracking?awb={awb}",
    "DTDC": "https://www.dtdc.in/tracking/shipment-tracking.asp?awb={awb}",
    "Delhivery": "https://www.delhivery.com/track/package/{awb}",
    "FedEx": "https://www.fedex.com/fedextrack/?trknbr={awb}",
    "Trackon": "https://trackon.in/tracking?awb={awb}",
    "Speed Post": "https://www.indiapost.gov.in/_layouts/15/dpt.cept.tracking/trackconsignment.aspx",
    "Professional Couriers": "https://www.tpcindia.com/tracking.aspx?awb={awb}",
    "Internal Fleet": ""
}

# ── 5. Standard Geographical Zones / Regions ──────────────────────────────────
REGIONS: List[str] = ["North", "South", "East", "West", "Central"]

# ── 6. Operational Status Lifecycles ──────────────────────────────────────────
DISPATCH_STATUSES = [
    "PENDING",        # Consignment created, awaiting courier booking
    "DISPATCHED",     # AWB assigned, dispatched from central hub
    "IN_TRANSIT",     # En route through courier transit hubs
    "DELIVERED",      # Carrier marked as delivered at local destination
    "RETURNED"        # Delivery failed / returned to origin
]

VERIFICATION_STATUSES = [
    "PENDING",        # Physical receipt not yet confirmed by local SPOC
    "CONFIRMED",      # SPOC has physically verified contents on-site
    "DISCREPANCY"     # Box received with damaged or missing items
]
