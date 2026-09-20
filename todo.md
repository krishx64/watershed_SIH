# Implementation Roadmap & Official API Integration Guide (PS-26015)

---

## 1. What are SRISHTI and DRISHTI?

Under the **Integrated Watershed Management Programme (IWMP)** — now known as the **Watershed Development Component of Pradhan Mantri Krishi Sinchayee Yojana (WDC-PMKSY)** — the Department of Land Resources (DoLR), Ministry of Rural Development (MoRD), partnered with **ISRO / NRSC (National Remote Sensing Centre)** to build a national monitoring system.

### **DRISHTI (दृष्टि — The Ground Mobile App)**
* **What it is**: An Android-based field data-collection app built by NRSC/ISRO for ground-level field officers, Watershed Development Teams (WDT), and Project Implementing Agencies (PIA).
* **What it captures**: When a conservation structure (check dam, farm pond, percolation tank, contour bund, afforestation plot) is executed:
  1. **Geo-tagged photos** (two time-stamped photographs taken from ground level).
  2. **High-precision GPS coordinates** (latitude, longitude, altitude, accuracy).
  3. **Asset metadata**: Project ID, state/district, work code, asset type, stage of construction (before/during/after).
* **Where it goes**: Automatically uploaded over cellular network directly to NRSC Bhuvan servers.

### **SRISHTI (सृष्टि — The Web GIS Monitoring Geoportal)**
* **What it is**: The official web GIS monitoring portal hosted at `https://bhuvan-app1.nrsc.gov.in/iwmp`.
* **What it does**:
  1. Visualizes micro-watershed boundary polygons across India at 1:50,000 scale.
  2. Plots every uploaded DRISHTI ground photo as an interactive pin on top of Indian satellite imagery (IRS Resourcesat / Cartosat / LISS-III).
  3. Provides administrative dashboards for District Collectors, State Nodal Agencies (SLNA), and MoRD to track physical and financial progress.

### **The Fundamental Gap Highlighted by Problem Statement 26015**
> **Current Reality**: DRISHTI photos are treated merely as *administrative documentation* (proof that funds were disbursed and concrete was poured).  
> **What is Missing**: There is **no automated spatial analysis or remote-sensing verification** checking whether the structure:
> 1. Was built in the hydro-dynamically correct drainage channel.
> 2. Actually captured water or reduced runoff.
> 3. Created positive upstream/downstream vegetation impact over a 3–5 year window.
>
> **Watershed Signal's Role**: To bridge DRISHTI field photos with satellite analytics into an explainable, automated decision-support engine.

---

## 2. Official Government API & Data Source Specifications

The platform is designed around a decoupled **Data Ingestion Seam** (`data_adapter_design.md`). Below are the exact technical specifications for the official government endpoints.

```text
┌────────────────────────────────────────────────────────────────────────────────┐
│                           GOVERNMENT DATA SOURCES                              │
│                                                                                │
│   ┌────────────────────────┐  ┌─────────────────────────┐  ┌───────────────┐   │
│   │    SRISHTI-DRISHTI     │  │       ISRO Bhuvan       │  │   Bhoonidhi   │   │
│   │   (Field Geo-Photos)   │  │   (LULC Stats & DEM)    │  │  (LISS-III)   │   │
│   └───────────┬────────────┘  └────────────┬────────────┘  └───────┬───────┘   │
└───────────────┼────────────────────────────┼───────────────────────┼───────────┘
                │                            │                       │
                ▼                            ▼                       ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                      BHUVAN / BHOONIDHI DATA ADAPTER                           │
│                       (project/src/bhuvan_adapter.py)                          │
│                                                                                │
│   • Daily Token Negotiation via Bhuvan OAuth (`oauth/key.php`)                 │
│   • CartoDEM GeoTIFF Tile Extraction (`curl_gdal_api.php`)                     │
│   • Watershed AOI LULC Class Aggregation (`curl_aoi.php`)                      │
│   • Census 2001 Demographic Proximity Enrichment (`curl_reverse_village.php`)  │
└──────────────────────────────────────┬─────────────────────────────────────────┘
                                       │
                        Normalized Raster & Vector Seam
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                      CORE ANALYTICAL PIPELINE (EXISTING)                       │
│     • Flow Delineation • U-Net LULC • Change Detection • Evidence Fusion       │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

### A. ISRO Bhuvan REST APIs (`bhuvan-app1.nrsc.gov.in/api/`)

#### 1. Access Token Negotiation
* **Endpoint**: `POST https://bhuvan-app1.nrsc.gov.in/api/oauth/key.php`
* **Prerequisite**: Active user login session on Bhuvan.
* **Payload**: `theme=<theme_name>` (Options: `geoid`, `lulc_aoi`, `lulc_dist`, `route`, `vg`, `vrg`)
* **Lifespan**: Tokens expire after **24 hours**.

#### 2. CartoDEM Satellite Elevation Download API
* **Endpoint**: `GET https://bhuvan-app1.nrsc.gov.in/api/geoid/curl_gdal_api.php`
* **Headers**: `Content-Type: application/x-www-form-urlencoded`
* **Parameters**:
  * `id`: CartoDEM tile sheet identifier (e.g. `cdnc43e` for Survey of India grid).
  * `datum`: `geoid` (converted using GDAL) or `elipsoid` (raw satellite elevation).
  * `se`: `CDEM`
  * `key`: Active Bhuvan token for theme `geoid`.
* **Output**: `.zip` archive containing the official 30m/10m GeoTIFF elevation raster.

#### 3. 50k LULC Area-of-Interest (AOI) Statistics API
* **Endpoint**: `GET https://bhuvan-app1.nrsc.gov.in/api/lulc/curl_aoi.php`
* **Headers**: `Content-Type: application/x-www-form-urlencoded`
* **Parameters**:
  * `geom`: Bounding polygon in WKT format: `POLYGON((lon1 lat1, lon2 lat2, ..., lon1 lat1))`
  * `token`: Active token for theme `lulc_aoi`.
* **Output**: JSON array detailing state-wise area distribution across NRSC classes (`l01`–`l24`):
  ```json
  [
    {
      "State": "MH",
      "'l01'": 0.54,
      "'l02'": 1.20,
      "'l04'": 142.30,
      "'l06'": 45.10,
      "'l16'": 28.40,
      "'l18'": 3.10,
      "'l22'": 2.10,
      "'l23'": 4.80
    }
  ]
  ```
  *(Reference codes: `l04` = Cropland, `l06` = Fallow, `l08-l11` = Forest types, `l16` = Scrubland, `l18` = Barren rocky, `l22` = Rivers/Canals, `l23` = Reservoirs/Ponds).*

#### 4. 250k Multi-Year LULC Time-Series API
* **Endpoint**: `GET https://bhuvan-app1.nrsc.gov.in/api/lulc250k/curl_lulc250k.php`
* **Parameters**:
  * `polygon`: Polygon in WKT format.
  * `year`: Single year (e.g. `2018_19`), comma-separated (e.g. `2005_06,2015_16`), or `all` (2004–2019).
  * `option`: `json` (for programmatic parsing) or `chart` (SVG visual).
  * `token`: Active token for theme `laoi`.
* **Output**: Longitudinal trend breakdown across 15 years for the watershed AOI.

#### 5. Village Reverse Geocoding & Demographics API
* **Endpoint**: `GET https://bhuvan-app1.nrsc.gov.in/api/api_proximity/curl_reverse_village.php`
* **Parameters**:
  * `lat`: Decimal latitude (e.g. `16.2793`).
  * `lon`: Decimal longitude (e.g. `80.5883`).
  * `token`: Active token for theme `vrg`.
* **Output**: Census 2001 demographic record:
  ```json
  [
    {
      "name1": "KADWANCHI",
      "vid": "2817004002130200",
      "no_hh": "412",
      "tot_p": "2340",
      "tot_m": "1210",
      "tot_f": "1130",
      "m_lit": "890",
      "f_lit": "640",
      "dhq_name": "JALNA",
      "thq_name": "JALNA"
    }
  ]
  ```

---

### B. Bhoonidhi Satellite Catalog (`bhoonidhi.nrsc.gov.in`)

* **Target Sensor**: **Resourcesat-2 / 2A LISS-III**
* **Spatial Resolution**: 23.5 meters (~30m optical, satisfying PS-26015 requirements).
* **Spectral Bands**:
  * Band 2 (Green): 0.52 – 0.59 µm
  * Band 3 (Red): 0.62 – 0.68 µm
  * Band 4 (NIR): 0.77 – 0.86 µm
  * Band 5 (SWIR): 1.55 – 1.70 µm
* **Temporal Pairing**:
  * `T1 (Pre-Intervention Baseline)`: Dec 2019 – March 2020 (Dry season).
  * `T2 (Post-Intervention Current)`: Dec 2024 – March 2025 (Dry season).

---

### C. SRISHTI-DRISHTI Field Assets Extraction (`bhuvan-app1.nrsc.gov.in/iwmp`)

* **Access Route**: Bhuvan Login $\rightarrow$ `IWMP/SRISHTI Module` $\rightarrow$ Select State/District $\rightarrow$ Filter by Conservation Works.
* **Extraction Schema**:
  * `asset_id`: Unique identifier assigned by DRISHTI mobile app.
  * `work_type`: `Check Dam`, `Percolation Tank`, `Farm Pond`, `Contour Bund`, `Loose Boulder Structure`.
  * `lat`, `lon`: Ground-truth GPS coordinates.
  * `photo_1_url`, `photo_2_url`: High-resolution field photos taken on-site.
  * `execution_year`: Year of asset completion.

---

## 3. Actionable Implementation Checklist

### Phase 1: Authentication & Configuration Setup
- [x] **1.1 Bhuvan API Token Setup**:
  - Registered and authenticated via `https://bhuvan-app1.nrsc.gov.in/api/`.
  - Configured active tokens in `.env` (`BHUVAN_TOKEN_LULC`, `BHUVAN_TOKEN_GEOID`, `BHUVAN_TOKEN_VRG`).
- [x] **1.2 Update Environment & Configurations**:
  - Added Bhuvan API URLs, headers, and fallback timeout handlers in `project/src/data_adapter.py`.
  - Automated Redis cache with in-memory fallback.

---

### Phase 2: Ingestion Adapter Module (`project/src/data_adapter.py`)
- [x] **2.1 Implement Unified Government Data Adapter**:
  - `fetch_bhuvan_aoi_stats(bbox)`: Calls `/api/lulc/curl_aoi.php`, parses official NRSC classes (`l01`–`l24`), computes square kilometer areas and percentages, and caches with 24h TTL.
  - `load_or_fetch_optical_date(bbox, date_tag, ...)`: Auto-detects Bhoonidhi coverage; streams via `/vsizip/` if present or falls back to AWS Sentinel-2.
- [x] **2.2 Implement Graceful High-Availability Fallback**:
  - Automated fallback to AWS S3 Open Data (Sentinel-2 L2A + Copernicus 30m DEM) when querying arbitrary Indian locations (verified live on Kolkata and Pune).

---

### Phase 3: SRISHTI-DRISHTI Field Verification Integration
- [x] **3.1 Geotagged Field Evidence Engine**:
  - Standardized inspection schema in `project/data/field_validation_log.csv` and interventions in `project/data/interventions.csv`.
  - 5-point spatial evidence fusion engine in `FieldTab.tsx` linking photos, DEM catchment boundaries, drainage channels, and change masks.
- [ ] **3.2 Additional Field Photos (Optional Expansion)**:
  - If field teams provide additional raw geotagged check-dam photos, save to `project/data/field_photos/` and register in CSV.

---

### Phase 4: Bhoonidhi Indian Satellite Data Pairing
- [x] **4.1 Ingest Native Resourcesat-2A LISS-III Imagery**:
  - 13 scenes loaded in `project/bhoonidhi_data/` covering Kadwanchi Watershed (Path 097 Row 058).
  - Multi-temporal auto-pairing: T1 (`2025-12-27`) and T2 (`2026-03-09`).
- [x] **4.2 Zero-Extraction Virtual Raster Streaming**:
  - Direct `/vsizip/` access without disk unzipping (1.66-second extraction benchmark).
  - Native 23.5m pixels resampled to 10m grid with synthetic blue proxy, NDVI, and NDWI to form Model 1's 6-channel tensor.

### Phase 5: Scientific Validation Dashboard Integration
- [x] **5.1 Display Official Bhuvan Statistics**:
  - Integrated official ISRO Bhuvan 50k ground-truth table into `web/src/components/tabs/ValidationTab.tsx`.
  - Live side-by-side comparison of official government areas (km² and %) against Model 1 U-Net predictions.
- [x] **5.2 Active Sensor Attribution & Kadwanchi Quick-Run**:
  - Dynamic sensor attribution badge in header (`ISRO Bhoonidhi LISS-III` vs `Sentinel-2 L2A Fallback`).
  - Featured **Kadwanchi Watershed (ISRO Bhoonidhi + Bhuvan Ground Truth)** quick-run query in UI.

---

### Phase 6: Production Hardening, Redis Raster Streaming & Executive Reporting
- [x] **6.1 Zero Public Folder Writes & Redis In-Memory Image Store**:
  - Replaced transient disk writes into `web/public/demo-data/` with binary Redis caching (`image:{site_key}:{image_name}`) with 24h TTL.
  - Added binary streaming endpoint `GET /api/images/{site_key}/{image_name}` with Next.js proxy rewrite for zero-latency, zero-pollution delivery.
- [x] **6.2 Strict Month & Year Temporal Selection**:
  - Removed daily date pickers; restricted temporal selections strictly to Month & Year (`YYYY-MM`) matching physical satellite orbits with seasonal presets.
- [x] **6.3 Dedicated 9th Tab: ISRO Bhuvan Ground-Truth Cross-Validation Report (`BhuvanReportTab.tsx`)**:
  - Executive tripartite sign-offs (NRSC/ISRO, MoRD/WDC-PMKSY, Project Lead) and Document ID.
  - Official verified link to live Bhuvan IWMP GIS geoportal (`https://bhuvan-app1.nrsc.gov.in/iwmp/`).
  - Multi-class alignment convergence (73.3% overall, 97.1% agriculture cropland).
  - High-contrast `@media print` layout and complete JSON export.

### Phase 7: Real-Time Cancellation, Geocoding Proxy & Operational Hardening (Sep 2026)
- [x] **7.1 In-Flight Pipeline Cancellation & Non-Blocking Worker Shutdown**:
  - Added `POST /api/pipeline/cancel` and non-blocking 100ms polling loop with `pool.shutdown(wait=False, cancel_futures=True)`.
  - Added interactive animated red `[Cancel Analysis ✕]` button directly on the search bar in `LocationPicker.tsx`.
- [x] **7.2 Server-Side Geocoding Reverse Proxy**:
  - Implemented `GET /api/geocode?q=...` with compliant User-Agent headers, preventing browser CORS / Forbidden header failures.
- [x] **7.3 Process-Isolated Atomic File Writes**:
  - Hardened `atomic_raster_write` with PID/UUID temp files in `config.py` preventing race conditions during concurrent searches.
- [x] **7.4 Bhoonidhi Failover & Pre-Warming Documentation**:
  - Documented geographic coverage rationale and offline CLI pre-warming workflow (`bhoonidhi_prewarm.py`).

---

## 4. Hackathon Defense & Positioning (SIH PS-26015)

When presenting to evaluators, use this precise positioning:

> *"Watershed Signal does not compete with or duplicate SRISHTI-DRISHTI or Bhuvan. Instead, it serves as the **analytical intelligence layer** that the government platform currently lacks.*  
> *DRISHTI collects the ground-truth photos; Bhuvan and Bhoonidhi host the elevation and satellite catalogs. Watershed Signal ingests these through a standardized data adapter, performs AI land-cover segmentation and bi-temporal change detection, and produces actionable decision cards for field officers."*
