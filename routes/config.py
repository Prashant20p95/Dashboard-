"""
OpsCommand — Configuration & System Metadata API
=================================================
Exposes dynamic organization branding, item definitions, courier integrations,
and system status to the frontend Single-Page Application.
"""
from fastapi import APIRouter
import config

router = APIRouter()

@router.get("")
@router.get("/")
def get_system_config():
    """
    Returns dynamic system configuration.
    The frontend calls this on startup to dynamically configure portal title,
    organization name, table columns, item names, and carrier dropdowns.
    """
    return {
        "organization_name": config.ORGANIZATION_NAME,
        "portal_title": config.PORTAL_TITLE,
        "portal_subtitle": config.PORTAL_SUBTITLE,
        "app_version": config.APP_VERSION,
        "support_phone": config.SUPPORT_PHONE,
        "support_email": config.SUPPORT_EMAIL,
        "default_currency": config.DEFAULT_CURRENCY,
        "at_risk_threshold_days": config.AT_RISK_THRESHOLD_DAYS,
        "tracked_items": config.TRACKED_ITEMS,
        "couriers": list(config.COURIER_PARTNERS.keys()),
        "courier_tracking_urls": config.COURIER_PARTNERS,
        "regions": config.REGIONS,
        "dispatch_statuses": config.DISPATCH_STATUSES,
        "verification_statuses": config.VERIFICATION_STATUSES
    }
