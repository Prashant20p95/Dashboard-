"""
OpsCommand — Database Seeder & Demo Data Generator
===================================================
1. Seeds default collateral items on first startup.
2. Provides `seed_demo_data()` to generate 25 diverse regional distribution hubs,
   multi-carrier consignments (BlueDart, DTDC, Delhivery, FedEx), realistic
   AWB tracking numbers, and verified delivery records for instant preview.
"""
from datetime import date, datetime, timedelta
import json
import random

from database import SessionLocal
from models import Event, CollateralItem, EventDestination, Dispatch, DispatchItem, DeliveryConfirmation
import config

COLLATERAL_ITEMS = [
    {
        "code": "ITEM_PRIMARY",
        "name": "Primary Pass / Kit",
        "category": "CORE",
        "unit": "pcs",
        "description": "Standard participant / attendee identification pass or core event kit.",
    },
    {
        "code": "ITEM_SECONDARY",
        "name": "Secondary Pack",
        "category": "CORE",
        "unit": "pcs",
        "description": "Special delegate passes, secondary vouchers, or auxiliary collateral.",
    },
    {
        "code": "ITEM_VIP",
        "name": "VIP / Executive Kit",
        "category": "PREMIUM",
        "unit": "pcs",
        "description": "Executive pass, VIP package, or premium identification bundle.",
    },
    {
        "code": "ITEM_ACCESSORY",
        "name": "Lanyards & Badges",
        "category": "ACCESSORY",
        "unit": "pcs",
        "description": "Branded lanyards, badge holders, or stationery accessories.",
    },
]


def seed_collateral_items():
    """Insert master collateral items if not present."""
    db = SessionLocal()
    try:
        existing_codes = {c.code for c in db.query(CollateralItem).all()}
        added = False
        for item in COLLATERAL_ITEMS:
            if item["code"] not in existing_codes:
                db.add(CollateralItem(**item))
                added = True
        if added:
            db.commit()
    finally:
        db.close()


def seed_demo_data():
    """
    Generate realistic multi-region operational demonstration data.
    Populates 25 diverse regional distribution hubs, dispatches, and confirmations.
    """
    db = SessionLocal()
    try:
        # 1. Ensure master items exist
        seed_collateral_items()

        # 2. Create or find default event/campaign
        event = db.query(Event).filter(Event.event_code == "OPS-2026-PAN-INDIA").first()
        if not event:
            event = Event(
                event_code="OPS-2026-PAN-INDIA",
                name=f"{config.ORGANIZATION_NAME} — Pan-India Operations Campaign",
                city="Central Logistics HQ",
                state="National",
                venue="All Regional Hubs",
                start_date=date.today() + timedelta(days=2),
                end_date=date.today() + timedelta(days=30),
                delivery_deadline=date.today() + timedelta(days=1),
                status="ACTIVE",
                notes="Central operational tracking and dispatch distribution program."
            )
            db.add(event)
            db.commit()
            db.refresh(event)

        # If destinations already exist, skip re-seeding
        if db.query(EventDestination).filter(EventDestination.event_id == event.id).count() > 0:
            print("Demo destinations already exist. Skipping seed.")
            return

        # 3. Sample Regional Stations / Hubs
        sample_stations = [
            ("Mumbai Central Logistics Hub", "Maharashtra", "Mumbai", "West", "Rajesh Sharma", "9820112345", 2, "CONFIRMED", "BlueDart", "BD78491023"),
            ("Delhi NCR Distribution Center", "Delhi", "New Delhi", "North", "Amit Verma", "9811223344", 1, "CONFIRMED", "Delhivery", "DEL90214812"),
            ("Bengaluru South Hub", "Karnataka", "Bengaluru", "South", "Priya Nair", "9845012789", 3, "DELIVERED", "BlueDart", "BD88392014"),
            ("Kolkata East Terminal", "West Bengal", "Kolkata", "East", "Subhash Mukherjee", "9830198765", 4, "IN_TRANSIT", "DTDC", "DTDC6541289"),
            ("Hyderabad Central Depot", "Telangana", "Hyderabad", "South", "Kiran Reddy", "9849065432", 5, "IN_TRANSIT", "BlueDart", "BD90123847"),
            ("Ahmedabad Sector 4 Hub", "Gujarat", "Ahmedabad", "West", "Bhavin Patel", "9825043210", 6, "DELIVERED", "Delhivery", "DEL77889901"),
            ("Chennai Metro Distribution", "Tamil Nadu", "Chennai", "South", "Karthik Raman", "9840134567", 7, "CONFIRMED", "DTDC", "DTDC9988112"),
            ("Pune Logistics Center", "Maharashtra", "Pune", "West", "Sanjay Deshmukh", "9822098765", 8, "CONFIRMED", "BlueDart", "BD44556677"),
            ("Jaipur Regional Hub", "Rajasthan", "Jaipur", "North", "Vikram Singh", "9829012345", 2, "IN_TRANSIT", "FedEx", "FX889911223"),
            ("Lucknow Central Depot", "Uttar Pradesh", "Lucknow", "Central", "Manoj Pandey", "9415012345", 3, "PENDING", "BlueDart", "AWB Pending"),
            ("Patna East Facility", "Bihar", "Patna", "East", "Rakesh Kumar", "9431054321", 1, "IN_TRANSIT", "Trackon", "TRK33445566"),
            ("Bhopal Distribution Point", "Madhya Pradesh", "Bhopal", "Central", "Sunil Chouhan", "9425098765", 4, "CONFIRMED", "Delhivery", "DEL11223344"),
            ("Chandigarh North Depot", "Punjab", "Chandigarh", "North", "Gurpreet Singh", "9814012345", 5, "DELIVERED", "BlueDart", "BD55667788"),
            ("Guwahati Northeast Hub", "Assam", "Guwahati", "East", "Biplab Das", "9435012345", 9, "IN_TRANSIT", "BlueDart", "BD12345678"),
            ("Kochi South Terminal", "Kerala", "Kochi", "South", "Anand Menon", "9847054321", 10, "CONFIRMED", "DTDC", "DTDC4433221"),
            ("Indore Commercial Hub", "Madhya Pradesh", "Indore", "Central", "Nitin Joshi", "9826012345", 6, "DELIVERED", "FedEx", "FX776655443"),
            ("Visakhapatnam Coastal Depot", "Andhra Pradesh", "Visakhapatnam", "South", "Suresh Raju", "9848012345", 11, "PENDING", "BlueDart", "AWB Pending"),
            ("Nagpur Logistics Center", "Maharashtra", "Nagpur", "Central", "Pravin Tijare", "9823054321", 12, "CONFIRMED", "Delhivery", "DEL99001122"),
            ("Coimbatore South Hub", "Tamil Nadu", "Coimbatore", "South", "Ganesh Murthy", "9842012345", 13, "CONFIRMED", "BlueDart", "BD88112233"),
            ("Bhubaneswar Terminal", "Odisha", "Bhubaneswar", "East", "Alok Mohanty", "9437012345", 2, "DELIVERED", "DTDC", "DTDC7766551"),
            ("Surat Diamond City Hub", "Gujarat", "Surat", "West", "Paresh Shah", "9824012345", 14, "IN_TRANSIT", "Delhivery", "DEL44556611"),
            ("Varanasi Logistics Depot", "Uttar Pradesh", "Varanasi", "Central", "Akhilesh Mishra", "9450012345", 15, "PENDING", "BlueDart", "AWB Pending"),
            ("Dehradun Foothills Point", "Uttarakhand", "Dehradun", "North", "Rohit Rawat", "9412012345", 16, "CONFIRMED", "FedEx", "FX332211998"),
            ("Ranchi Regional Center", "Jharkhand", "Ranchi", "East", "Deepak Sahay", "9431154321", 1, "IN_TRANSIT", "Trackon", "TRK77889900"),
            ("Goa Coastal Hub", "Goa", "Panaji", "West", "Mario Fernandes", "9822154321", 18, "CONFIRMED", "BlueDart", "BD33445522")
        ]

        for idx, (name, state, city, region, spoc, mobile, days_offset, stage, courier, awb) in enumerate(sample_stations, 1):
            dest_code = f"LOC-{idx:03d}"
            ev_date = date.today() + timedelta(days=days_offset)
            
            # Quota allocation
            primary_qty = random.randint(300, 800)
            secondary_qty = random.randint(50, 200)
            vip_qty = random.randint(20, 80)
            lanyards_qty = primary_qty + secondary_qty + vip_qty

            req_qties = {
                "ITEM_PRIMARY": primary_qty,
                "ITEM_SECONDARY": secondary_qty,
                "ITEM_VIP": vip_qty,
                "ITEM_ACCESSORY": lanyards_qty
            }

            destination = EventDestination(
                event_id=event.id,
                destination_name=name,
                state=state,
                city=city,
                district=city,
                address_line1=f"Plot {idx * 12}, Logistics Industrial Area, Phase {idx % 3 + 1}",
                pin=f"{100000 + idx * 177:06d}",
                contact_person=spoc,
                mobile=mobile,
                event_date=ev_date,
                required_quantities_json=json.dumps(req_qties)
            )
            db.add(destination)
            db.flush()

            # Create consignment dispatch
            courier_status = "DELIVERED" if stage in ("DELIVERED", "CONFIRMED") else ("IN_TRANSIT" if stage == "IN_TRANSIT" else "PENDING")
            dispatch_date = date.today() - timedelta(days=max(1, 10 - days_offset))
            actual_del_date = (date.today() - timedelta(days=1)) if stage in ("DELIVERED", "CONFIRMED") else None

            dispatch = Dispatch(
                dispatch_code=f"DSP-{destination.id}-1",
                event_id=event.id,
                destination_id=destination.id,
                hist_organiser_name=name,
                hist_contact_person=spoc,
                hist_mobile=mobile,
                hist_address_line1=destination.address_line1,
                hist_city=city,
                hist_state=state,
                hist_pin=destination.pin,
                dispatch_date=dispatch_date,
                courier_partner=courier,
                awb_number=awb,
                courier_status=courier_status,
                box_count=f"{random.randint(1, 3)} Box(es)",
                actual_delivery_date=actual_del_date
            )
            db.add(dispatch)
            db.flush()

            # Add dispatch item contents
            db.add(DispatchItem(dispatch_id=dispatch.id, collateral_code="ITEM_PRIMARY", quantity=primary_qty))
            db.add(DispatchItem(dispatch_id=dispatch.id, collateral_code="ITEM_SECONDARY", quantity=secondary_qty))
            db.add(DispatchItem(dispatch_id=dispatch.id, collateral_code="ITEM_VIP", quantity=vip_qty))
            db.add(DispatchItem(dispatch_id=dispatch.id, collateral_code="ITEM_ACCESSORY", quantity=lanyards_qty))

            # Delivery confirmation
            if stage == "CONFIRMED":
                conf = DeliveryConfirmation(
                    dispatch_id=dispatch.id,
                    confirmation_status="CONFIRMED",
                    confirmed_by_name=spoc,
                    confirmation_method="PHONE_CALL",
                    confirmation_date=datetime.utcnow() - timedelta(hours=random.randint(2, 48)),
                    notes="Consignment physically received, inspected, and verified on-site."
                )
                db.add(conf)
            elif stage == "DELIVERED":
                conf = DeliveryConfirmation(
                    dispatch_id=dispatch.id,
                    confirmation_status="PENDING",
                    confirmed_by_name=spoc,
                    confirmation_method="PENDING",
                    notes="Carrier marked delivered. Awaiting physical verification call."
                )
                db.add(conf)

        db.commit()
        print("Successfully seeded 25 regional hubs with consignments and tracking!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding demo data: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("Initializing database and seeding demo operational data...")
    from database import init_db
    init_db()
    seed_collateral_items()
    seed_demo_data()
    print("Done! You can now start the server with: python main.py")
