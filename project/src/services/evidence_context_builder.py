import uuid
from datetime import datetime, timezone
from typing import Dict, Any

from storage.database import get_geo_photo, save_analysis_run, update_geo_photo_status, save_evidence_finding
from services.geo_photo_service import resolve_context
from aoi_picker import bbox_around, run_pipeline
from tier1_fallback import summarize_changes

def _generate_findings(photo: Dict[str, Any], health: float, trend: float, alerts: list, change_summary: dict) -> list:
    """
    Generates structured findings based on evidence fusion and explainable rules.
    """
    findings = []
    
    # 1. Degradation check
    if trend < -0.05 or change_summary.get("degradation", {}).get("hectares", 0) > 1.0:
        findings.append({
            "finding_type": "POTENTIAL_LAND_DEGRADATION",
            "severity": "HIGH",
            "evidence_strength": "HIGH" if photo.get("latitude") else "MEDIUM",
            "explanation": "Significant vegetation loss detected near observation point alongside negative NDVI trend."
        })
        
    # 2. Water context
    if change_summary.get("water_gain", {}).get("hectares", 0) > 0.5:
        findings.append({
            "finding_type": "WATER_PRESENCE_CORROBORATION",
            "severity": "INFO",
            "evidence_strength": "MEDIUM",
            "explanation": "Satellite indicates new water accumulation near field observation."
        })
        
    # 3. Add generated alerts
    for alert in alerts:
        findings.append({
            "finding_type": "SATELLITE_ALERT",
            "severity": "WARNING",
            "evidence_strength": "MEDIUM",
            "explanation": alert
        })
        
    return findings

def analyze_photo_context(photo_id: str, model, device) -> str:
    """
    Executes the analytical pipeline around the photo's location.
    Returns the run_id.
    """
    # 1. Ensure context is resolved
    context = resolve_context(photo_id)
    photo = get_geo_photo(photo_id)
    
    lat = context["latitude"]
    lon = context["longitude"]
    radius_km = 0.5 # Default localized radius for photo context
    
    run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
    
    # Initialize run record
    bbox = bbox_around(lat, lon, radius_km)
    run_record = {
        "run_id": run_id,
        "photo_id": photo_id,
        "watershed_id": context["watershed_id"],
        "aoi_geometry": str(bbox),
        "radius_m": radius_km * 1000,
        "t1_date": context["satellite"]["t1"],
        "t2_date": context["satellite"]["t2"],
        "status": "RUNNING",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "error_message": None
    }
    save_analysis_run(run_record)
    update_geo_photo_status(photo_id, "analysis_status", "RUNNING")
    
    try:
        site_key = f"photo_{photo_id}"
        # Trigger the existing analytical pipeline
        (results, change_map, health, trend, alerts,
         watershed_mask, drainage_network, pour_point, watershed_caveat, watershed_context) = run_pipeline(
            bbox, site_key, model, device
        )
        
        change_summary_raw = summarize_changes(change_map)
        
        # Evidence Fusion & Findings Generation
        findings = _generate_findings(photo, health, trend, alerts, change_summary_raw)
        
        for f in findings:
            finding_id = f"FND-{uuid.uuid4().hex[:8].upper()}"
            f_record = {
                "finding_id": finding_id,
                "run_id": run_id,
                "finding_type": f["finding_type"],
                "severity": f["severity"],
                "evidence_strength": f["evidence_strength"],
                "explanation": f["explanation"],
                "status": "AWAITING_VERIFICATION",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            save_evidence_finding(f_record)
            
        # Complete run
        run_record["status"] = "COMPLETED"
        run_record["completed_at"] = datetime.now(timezone.utc).isoformat()
        save_analysis_run(run_record)
        update_geo_photo_status(photo_id, "analysis_status", "COMPLETED")
        
    except Exception as e:
        run_record["status"] = "FAILED"
        run_record["error_message"] = str(e)
        run_record["completed_at"] = datetime.now(timezone.utc).isoformat()
        save_analysis_run(run_record)
        update_geo_photo_status(photo_id, "analysis_status", "FAILED")
        raise
        
    return run_id
