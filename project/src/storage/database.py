import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Database path
DB_DIR = Path(__file__).resolve().parents[2] / "data" / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "watershed.db"

def _get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = _get_conn()
    c = conn.cursor()
    
    # 1. GeoPhoto Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS geo_photos (
            photo_id TEXT PRIMARY KEY,
            file_uri TEXT,
            thumbnail_uri TEXT,
            latitude REAL,
            longitude REAL,
            altitude REAL,
            gps_accuracy_m REAL,
            captured_at TEXT,
            source TEXT,
            watershed_id TEXT,
            intervention_id TEXT,
            metadata_status TEXT,
            analysis_status TEXT,
            created_at TEXT,
            sha256 TEXT
        )
    """)
    
    # 2. Analysis Run Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS analysis_runs (
            run_id TEXT PRIMARY KEY,
            photo_id TEXT,
            watershed_id TEXT,
            aoi_geometry TEXT,
            radius_m REAL,
            t1_date TEXT,
            t2_date TEXT,
            status TEXT,
            started_at TEXT,
            completed_at TEXT,
            error_message TEXT,
            FOREIGN KEY(photo_id) REFERENCES geo_photos(photo_id)
        )
    """)
    
    # 3. Evidence Findings Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS evidence_findings (
            finding_id TEXT PRIMARY KEY,
            run_id TEXT,
            finding_type TEXT,
            severity TEXT,
            evidence_strength TEXT,
            explanation TEXT,
            status TEXT,
            created_at TEXT,
            FOREIGN KEY(run_id) REFERENCES analysis_runs(run_id)
        )
    """)
    
    # 4. Field Verification Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS field_verifications (
            verification_id TEXT PRIMARY KEY,
            finding_id TEXT,
            officer_id TEXT,
            status TEXT,
            notes TEXT,
            verified_at TEXT,
            verification_photo_id TEXT,
            FOREIGN KEY(finding_id) REFERENCES evidence_findings(finding_id)
        )
    """)
    
    conn.commit()
    conn.close()

def save_geo_photo(data: Dict[str, Any]):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO geo_photos 
        (photo_id, file_uri, thumbnail_uri, latitude, longitude, altitude, gps_accuracy_m, captured_at, source, watershed_id, intervention_id, metadata_status, analysis_status, created_at, sha256)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("photo_id"), data.get("file_uri"), data.get("thumbnail_uri"), 
        data.get("latitude"), data.get("longitude"), data.get("altitude"), 
        data.get("gps_accuracy_m"), data.get("captured_at"), data.get("source"),
        data.get("watershed_id"), data.get("intervention_id"), data.get("metadata_status"),
        data.get("analysis_status"), data.get("created_at"), data.get("sha256")
    ))
    conn.commit()
    conn.close()

def get_geo_photo(photo_id: str) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM geo_photos WHERE photo_id = ?", (photo_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def update_geo_photo_status(photo_id: str, status_field: str, status_value: str):
    conn = _get_conn()
    c = conn.cursor()
    # Safely interpolate the field name since it's restricted
    if status_field not in ["metadata_status", "analysis_status"]:
        raise ValueError("Invalid status field")
        
    c.execute(f"UPDATE geo_photos SET {status_field} = ? WHERE photo_id = ?", (status_value, photo_id))
    conn.commit()
    conn.close()

def save_analysis_run(data: Dict[str, Any]):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO analysis_runs
        (run_id, photo_id, watershed_id, aoi_geometry, radius_m, t1_date, t2_date, status, started_at, completed_at, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("run_id"), data.get("photo_id"), data.get("watershed_id"),
        data.get("aoi_geometry"), data.get("radius_m"), data.get("t1_date"),
        data.get("t2_date"), data.get("status"), data.get("started_at"),
        data.get("completed_at"), data.get("error_message")
    ))
    conn.commit()
    conn.close()
    
def get_analysis_run(run_id: str) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM analysis_runs WHERE run_id = ?", (run_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def save_evidence_finding(data: Dict[str, Any]):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO evidence_findings
        (finding_id, run_id, finding_type, severity, evidence_strength, explanation, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("finding_id"), data.get("run_id"), data.get("finding_type"),
        data.get("severity"), data.get("evidence_strength"), data.get("explanation"),
        data.get("status"), data.get("created_at")
    ))
    conn.commit()
    conn.close()

def get_evidence_findings_by_run(run_id: str) -> List[Dict[str, Any]]:
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM evidence_findings WHERE run_id = ?", (run_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_field_verification(data: Dict[str, Any]):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO field_verifications
        (verification_id, finding_id, officer_id, status, notes, verified_at, verification_photo_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("verification_id"), data.get("finding_id"), data.get("officer_id"),
        data.get("status"), data.get("notes"), data.get("verified_at"), data.get("verification_photo_id")
    ))
    # Update the finding status
    if data.get("status") in ["CONFIRMED", "NOT_CONFIRMED"]:
        c.execute("UPDATE evidence_findings SET status = ? WHERE finding_id = ?", (data.get("status"), data.get("finding_id")))
    conn.commit()
    conn.close()

# Initialize DB on import
init_db()
