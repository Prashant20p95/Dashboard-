# OpsCommand — Enterprise Operations & Logistics Command Dashboard

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-WAL%20Mode-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Ready-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An enterprise-ready, white-label **Operations, Logistics & Consignment Command Dashboard** designed for pan-region distribution networks, corporate event passes, retail store rollouts, franchise collateral, and field supply chain tracking.

Built with **FastAPI**, high-performance **SQLite with Write-Ahead Logging (WAL)** (PostgreSQL-compatible), and a clean **Vanilla ES6 Single-Page Application (SPA)** following the high-density Linear / Stripe operational UI pattern.

---

## 1. Operational Philosophy & The 4-Question Glance

Traditional logistics spreadsheets and ERPs bury vital operational data under nested menus. OpsCommand is engineered to answer the **4 fundamental operational questions** in under 1 second:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. WHEN is the next milestone?                                              │
│    Exact schedule date, active operational wave, relative countdown badge.  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. WHERE is the destination?                                                │
│    Destination Hub/Venue, State/Region, SPOC contact name & verified phone. │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. IS THE CONSIGNMENT DELIVERED?                                            │
│    Courier carrier, live AWB tracking link, box count, item quota ledger.   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. WHICH DESTINATIONS ARE AT RISK?                                          │
│    Consignments approaching deadline that are not yet physically verified.  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Decoupled Delivery Verification Model
Standard couriers often mark consignments as "Delivered" when dropped at a facility gate or postal desk. OpsCommand decouples **Courier Transit Status** from **Physical On-Site Verification**:
- **Dispatched / In Transit**: Consignment is en route with assigned AWB.
- **Delivered (Courier)**: Carrier marked as delivered at local destination.
- **Confirmed / Verified**: Local SPOC on-site has physically opened the carton, verified the items, and confirmed receipt.

---

## 2. System Architecture

```mermaid
flowchart TD
    Client["Browser / Mobile Client (Vanilla ES6 SPA)"]
    API["FastAPI REST Backend (Async Python)"]
    ConfigEngine["Dynamic Configuration Layer (config.py & .env)"]
    DB[("SQLite WAL / PostgreSQL (SQLAlchemy ORM)")]
    TrackingEngine["Carrier Tracking URL Resolvers"]
    ExportEngine["OpenPyXL Excel Audit Engine"]
    LabelEngine["WYSIWYG Carton & Thermal Label Engine"]

    Client -->|HTTP / JSON Requests| API
    API -->|Dynamic JSON Responses| Client
    API --> ConfigEngine
    API --> DB
    API --> TrackingEngine
    API --> ExportEngine
    API --> LabelEngine
```

---

## 3. Project Structure

```
Dashboard-/
├── config.py                 # Central configuration (Single Source of Truth)
├── database.py               # SQLite WAL connection engine (PostgreSQL-ready)
├── main.py                   # FastAPI server entry point & router aggregation
├── models.py                 # SQLAlchemy ORM models (Destinations, Dispatches, Items, Verification)
├── schemas.py                # Pydantic request / response validation schemas
├── seed_data.py              # Realistic multi-region demo seeder (25 regional hubs)
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── .gitignore                # Production ignore rules
├── Dockerfile                # Production container definition
├── docker-compose.yml        # Multi-container orchestration
├── start_server.bat          # 1-click Windows launcher
├── start_server.sh           # 1-click Linux/macOS launcher
├── routes/
│   ├── config.py             # Dynamic organization metadata API (/api/config)
│   ├── dashboard.py          # Operational KPIs, status counters & telemetry
│   ├── dispatch.py           # Consignment pipeline, AWB assignments & statuses
│   ├── events.py             # Campaign & operations event schedule
│   ├── export_engine.py      # Multi-sheet Excel workbook export & audit
│   ├── organisers.py         # Destination directory & SPOC contacts
│   ├── printing.py           # WYSIWYG printable box & shipping labels
│   ├── datastore.py          # Database inspector & backup downloads
│   ├── tracking.py           # Multi-carrier tracking URL resolvers
│   ├── stock.py              # Collateral item inventory ledger
│   ├── billing.py            # Courier & printing invoice ledgers
│   ├── participants.py       # Attendee / recipient ledger & CSV parser
│   └── audit.py              # System change logs & audit trail
└── static/
    ├── index.html            # High-density operational Single-Page Application
    ├── styles.css            # Linear/Stripe design system (neutral palette, hairline borders)
    └── app.js                # Modular Vanilla ES6 frontend (reads /api/config dynamically)
```

---

## 4. Quickstart Guide

### Option A: Local Python Environment (Recommended for Development)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Prashant20p95/Dashboard-.git
   cd Dashboard-
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Seed the database with sample operational data:**
   ```bash
   python seed_data.py
   ```
   *This automatically generates 25 regional distribution hubs, dispatches, multi-carrier tracking AWBs, and verification states.*

5. **Start the application:**
   ```bash
   # Using Python
   python main.py

   # Or using the launcher scripts:
   .\start_server.bat       # Windows
   ./start_server.sh        # Linux / macOS
   ```

6. **Open your browser:**
   - Operational Dashboard: `http://127.0.0.1:8000`
   - Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`

---

### Option B: Docker Deployment (Recommended for Production)

Run the entire application in a container with a single command:

```bash
docker-compose up -d
```

The application will be accessible at `http://localhost:8000`.

---

## 5. White-Label & Customization Guide

OpsCommand is built from the ground up to be adapted for **any organization or enterprise** in minutes without modifying core business logic.

### Step 1: Organization Branding via `.env`
Create a `.env` file in the root directory (or copy from `.env.example`):

```ini
# Organization & Portal Branding
ORGANIZATION_NAME=Acme Logistics Global
PORTAL_TITLE=Acme Consignment & Dispatch Portal
PORTAL_SUBTITLE=Pan-Region Distribution & Delivery Verification System
APP_VERSION=2.0.0

# Operations Desk Contact
SUPPORT_PHONE=+91 98765 43210
SUPPORT_EMAIL=ops@acme.com
DEFAULT_CURRENCY=INR

# Operational Risk Threshold (Days until deadline to flag unverified consignments)
AT_RISK_THRESHOLD_DAYS=3
```

When you update these variables, the frontend topbar, document title, and reporting ledgers automatically update via the dynamic `/api/config/` endpoint!

---

### Step 2: Customizing Tracked Items & SKUs
In `config.py`, customize `TRACKED_ITEMS` to match your organization's physical deliverables:

```python
TRACKED_ITEMS = [
    {
        "code": "ITEM_PRIMARY",
        "name": "Standard Distribution Kit",
        "category": "CORE",
        "unit": "kits",
        "default_qty": 500,
        "description": "Standard participant or branch delivery kit."
    },
    {
        "code": "ITEM_SECONDARY",
        "name": "Marketing Collateral Pack",
        "category": "CORE",
        "unit": "packs",
        "default_qty": 100,
        "description": "Posters, banners, and promotional material."
    },
    {
        "code": "ITEM_VIP",
        "name": "Executive / Leadership Hamper",
        "category": "PREMIUM",
        "unit": "hampers",
        "default_qty": 25,
        "description": "Premium deliverables for VIP guests or branch managers."
    },
    {
        "code": "ITEM_ACCESSORY",
        "name": "Security Badges & Lanyards",
        "category": "ACCESSORY",
        "unit": "pcs",
        "default_qty": 600,
        "description": "Identification badges and accessories."
    }
]
```

---

### Step 3: Courier Tracking Integrations
Add or customize courier partners and their tracking URL templates in `config.py`:

```python
COURIER_PARTNERS = {
    "BlueDart": "https://www.bluedart.com/tracking?awb={awb}",
    "DTDC": "https://www.dtdc.in/tracking/shipment-tracking.asp?awb={awb}",
    "Delhivery": "https://www.delhivery.com/track/package/{awb}",
    "FedEx": "https://www.fedex.com/fedextrack/?trknbr={awb}",
    "DHL": "https://www.dhl.com/en/express/tracking.html?AWB={awb}",
    "Speed Post": "https://www.indiapost.gov.in/_layouts/15/dpt.cept.tracking/trackconsignment.aspx",
    "Internal Fleet": ""
}
```

---

### Step 4: Geographic Zones & Regions
Customize territorial regions in `config.py`:

```python
REGIONS = ["North", "South", "East", "West", "Central"]
```

---

## 6. Scaling to PostgreSQL

The codebase uses SQLAlchemy ORM and is 100% database-agnostic. To switch from the default SQLite engine to a production PostgreSQL database:

1. Install psycopg2 or asyncpg:
   ```bash
   pip install psycopg2-binary
   ```

2. In your `.env` file, change `DATABASE_URL`:
   ```ini
   DATABASE_URL=postgresql://username:password@db.yourdomain.com:5432/opscommand
   ```

3. Run the seeder to initialize the schema:
   ```bash
   python seed_data.py
   ```

---

## 7. API Reference

OpsCommand includes auto-generated OpenAPI / Swagger documentation:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/config/` | `GET` | Organization branding, item catalog & courier tracking URLs |
| `/api/dashboard/` | `GET` | 4-Question glance KPIs, telemetry & at-risk counters |
| `/api/organisers/` | `GET` | Filterable, paginated destinations with SPOC contacts & status |
| `/api/destinations/{id}` | `PATCH` | Quick inline edit of destination SPOC, dates, courier, AWB & stage |
| `/api/dispatch/` | `GET`, `POST` | Consignment dispatch ledger & consignment booking |
| `/api/export/quick/station-status-excel` | `GET` | Formatted multi-tab station delivery tracker Excel export |
| `/api/export/quick/dispatches-excel` | `GET` | Complete consignment dispatch manifest Excel export |
| `/api/datastore/backup-db` | `GET` | Instant raw database backup file download |

Access interactive API testing at `http://127.0.0.1:8000/docs`.

---

## 8. License

Distributed under the **MIT License**. See `LICENSE` for details. Free for commercial and private use.
